from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

from .parser import parse, StrikeEvent
from .clustering import cluster_events, Cluster
from .routes import build_route_graph, RouteEdge
from .temporal import analyze_temporal_patterns, TemporalPattern
from .logistics import analyze_logistics, RouteStats, ActivityPattern
from .storage import save_events, load_events, event_count


@dataclass
class Prediction:
    cluster_id: int
    lat: float
    lon: float
    earliest: datetime
    latest: datetime
    confidence: str        # 'high' / 'medium' / 'low'
    reason: str

    def __str__(self) -> str:
        return (
            f"Cluster {self.cluster_id} ({self.lat:.4f}, {self.lon:.4f})\n"
            f"  Window : {self.earliest.strftime('%Y-%m-%d %H:%M')} – "
            f"{self.latest.strftime('%H:%M')}\n"
            f"  Confidence: {self.confidence}\n"
            f"  Reason : {self.reason}"
        )


class PatternAnalyzer:
    def __init__(self, radius_km: float = 5.0, min_samples: int = 2, max_gap_hours: float = 6.0):
        self.radius_km = radius_km
        self.min_samples = min_samples
        self.max_gap_hours = max_gap_hours

        self.events: List[StrikeEvent] = []
        self.clusters: List[Cluster] = []
        self.labels: List[int] = []
        self.temporal: List[TemporalPattern] = []
        self.edges: dict = {}
        self.route_stats: List[RouteStats] = []
        self.activity: ActivityPattern = ActivityPattern()

    def load(self, text: str) -> "PatternAnalyzer":
        self.events = parse(text)
        return self

    def fit(self) -> "PatternAnalyzer":
        self.clusters, self.labels = cluster_events(
            self.events, self.radius_km, self.min_samples
        )
        _, self.edges = build_route_graph(
            self.clusters, self.labels, self.events, self.max_gap_hours
        )
        self.temporal = analyze_temporal_patterns(self.clusters)
        self.route_stats, self.activity = analyze_logistics(
            self.clusters, self.edges, self.events, self.labels
        )
        return self

    def ingest(self, text: str, source: Optional[str] = None) -> int:
        """Parse text, save to DB, reload all events, refit. Returns newly added count."""
        new_events = parse(text)
        added = save_events(new_events, source=source)
        self.events = load_events()
        return added

    def fit_from_db(self) -> "PatternAnalyzer":
        """Load all accumulated events from DB and fit."""
        self.events = load_events()
        return self.fit()

    def full_report(self, from_time: Optional[datetime] = None) -> str:
        from .report import generate_report
        if from_time is None:
            from_time = datetime.utcnow()
        predictions = self.predict(from_time)
        return generate_report(self, self.route_stats, self.activity, predictions, from_time)

    def predict(self, from_time: Optional[datetime] = None) -> List[Prediction]:
        if from_time is None:
            from_time = datetime.utcnow()

        tp_by_id = {t.cluster_id: t for t in self.temporal}
        cl_by_id = {c.id: c for c in self.clusters}
        predictions = []

        # 1. Predict revisit for each cluster based on temporal pattern
        for tp in self.temporal:
            if tp.avg_interval_sec is None:
                continue
            c = cl_by_id[tp.cluster_id]
            last_seen = tp.timestamps[-1]
            avg = timedelta(seconds=tp.avg_interval_sec)
            std = timedelta(seconds=tp.std_interval_sec or tp.avg_interval_sec * 0.2)

            expected = last_seen + avg
            if expected < from_time:
                # Slide forward in whole intervals until it's in the future
                elapsed = from_time - last_seen
                n = int(elapsed / avg) + 1
                expected = last_seen + avg * n

            confidence = (
                'high' if (tp.std_interval_sec or 0) < tp.avg_interval_sec * 0.25
                else 'medium' if (tp.std_interval_sec or 0) < tp.avg_interval_sec * 0.5
                else 'low'
            )

            predictions.append(Prediction(
                cluster_id=c.id,
                lat=c.center_lat,
                lon=c.center_lon,
                earliest=expected - std,
                latest=expected + std,
                confidence=confidence,
                reason=f"avg revisit interval {avg}, last seen {last_seen.strftime('%Y-%m-%d %H:%M')}",
            ))

        # 2. Predict positions along routes after the last known strike
        if self.events:
            last_event = max(self.events, key=lambda e: e.timestamp)
            last_label = self.labels[self.events.index(last_event)]

            if last_label != -1:
                for (src, dst), edge in self.edges.items():
                    if src != last_label:
                        continue
                    c = cl_by_id.get(dst)
                    if c is None:
                        continue
                    arrival = last_event.timestamp + timedelta(seconds=edge.avg_travel_time)
                    std_sec = (
                        max(e for e in edge.travel_times) - min(e for e in edge.travel_times)
                    ) / 2 if len(edge.travel_times) > 1 else edge.avg_travel_time * 0.2
                    predictions.append(Prediction(
                        cluster_id=dst,
                        lat=c.center_lat,
                        lon=c.center_lon,
                        earliest=arrival - timedelta(seconds=std_sec),
                        latest=arrival + timedelta(seconds=std_sec),
                        confidence='medium',
                        reason=f"route from cluster {src}, avg transit {timedelta(seconds=edge.avg_travel_time)}",
                    ))

        predictions.sort(key=lambda p: p.earliest)
        return predictions

    def summary(self) -> str:
        lines = [
            f"Events   : {len(self.events)}",
            f"Clusters : {len(self.clusters)}",
            f"Routes   : {len(self.edges)}",
        ]
        for c in self.clusters:
            tp = next((t for t in self.temporal if t.cluster_id == c.id), None)
            interval = (
                f"avg interval {tp.avg_interval}" if tp and tp.avg_interval else "single hit"
            )
            lines.append(f"  Cluster {c.id}: {c.size} strikes @ ({c.center_lat:.4f}, {c.center_lon:.4f}) — {interval}")
        return "\n".join(lines)
