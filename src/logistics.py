import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import timedelta
from collections import Counter

import numpy as np

from .clustering import Cluster
from .routes import RouteEdge
from .parser import StrikeEvent

EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = math.radians
    dlat = r(lat2 - lat1)
    dlon = r(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = math.radians
    dlon = r(lon2 - lon1)
    x = math.sin(dlon) * math.cos(r(lat2))
    y = math.cos(r(lat1)) * math.sin(r(lat2)) - math.sin(r(lat1)) * math.cos(r(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


@dataclass
class RouteStats:
    from_cluster: int
    to_cluster: int
    distance_km: float
    avg_speed_kmh: float
    min_speed_kmh: float
    max_speed_kmh: float
    transit_count: int
    bearing_deg: float              # direction of travel
    peak_hours: List[int]           # hours of day with most transits
    reliability: float              # 0..1, based on consistency of travel time

    @property
    def vehicle_class(self) -> str:
        if self.avg_speed_kmh < 5:
            return "foot/unknown"
        elif self.avg_speed_kmh < 30:
            return "slow vehicle / off-road"
        elif self.avg_speed_kmh < 80:
            return "truck / APC"
        elif self.avg_speed_kmh < 150:
            return "fast vehicle / car"
        else:
            return "aircraft"


@dataclass
class ActivityPattern:
    """Hour-of-day and day-of-week activity distribution across all events."""
    hour_counts: Dict[int, int] = field(default_factory=dict)
    dow_counts: Dict[int, int] = field(default_factory=dict)   # 0=Mon, 6=Sun

    @property
    def peak_hours(self) -> List[int]:
        if not self.hour_counts:
            return []
        threshold = max(self.hour_counts.values()) * 0.6
        return sorted(h for h, c in self.hour_counts.items() if c >= threshold)

    @property
    def peak_days(self) -> List[str]:
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if not self.dow_counts:
            return []
        threshold = max(self.dow_counts.values()) * 0.6
        return [days[d] for d, c in self.dow_counts.items() if c >= threshold]


def analyze_logistics(
    clusters: List[Cluster],
    edges: Dict[Tuple[int, int], RouteEdge],
    events: List[StrikeEvent],
    labels: List[int],
) -> Tuple[List[RouteStats], ActivityPattern]:

    cl_by_id = {c.id: c for c in clusters}

    # Global activity pattern
    activity = ActivityPattern()
    for e in events:
        h = e.timestamp.hour
        d = e.timestamp.weekday()
        activity.hour_counts[h] = activity.hour_counts.get(h, 0) + 1
        activity.dow_counts[d] = activity.dow_counts.get(d, 0) + 1

    # Per-route stats
    # Collect departure hours per route
    clustered_sorted = sorted(
        [(events[i], labels[i]) for i in range(len(events)) if labels[i] != -1],
        key=lambda x: x[0].timestamp,
    )
    route_hours: Dict[Tuple[int, int], List[int]] = {}
    for i in range(len(clustered_sorted) - 1):
        ev_a, cl_a = clustered_sorted[i]
        ev_b, cl_b = clustered_sorted[i + 1]
        if cl_a != cl_b:
            key = (cl_a, cl_b)
            route_hours.setdefault(key, []).append(ev_a.timestamp.hour)

    route_stats = []
    for (src, dst), edge in edges.items():
        ca = cl_by_id.get(src)
        cb = cl_by_id.get(dst)
        if ca is None or cb is None:
            continue

        dist = _haversine_km(ca.center_lat, ca.center_lon, cb.center_lat, cb.center_lon)
        bearing = _bearing_deg(ca.center_lat, ca.center_lon, cb.center_lat, cb.center_lon)

        speeds = [dist / (t / 3600) for t in edge.travel_times if t > 0]
        avg_speed = float(np.mean(speeds)) if speeds else 0.0
        min_speed = float(np.min(speeds)) if speeds else 0.0
        max_speed = float(np.max(speeds)) if speeds else 0.0

        # Reliability: low CV = consistent travel time
        if len(edge.travel_times) > 1:
            cv = float(np.std(edge.travel_times) / np.mean(edge.travel_times))
            reliability = max(0.0, 1.0 - cv)
        else:
            reliability = 0.5

        # Peak hours for this route
        hours = route_hours.get((src, dst), [])
        if hours:
            hour_counts = Counter(hours)
            threshold = max(hour_counts.values()) * 0.6
            peak = sorted(h for h, c in hour_counts.items() if c >= threshold)
        else:
            peak = []

        route_stats.append(RouteStats(
            from_cluster=src,
            to_cluster=dst,
            distance_km=dist,
            avg_speed_kmh=avg_speed,
            min_speed_kmh=min_speed,
            max_speed_kmh=max_speed,
            transit_count=edge.count,
            bearing_deg=bearing,
            peak_hours=peak,
            reliability=reliability,
        ))

    route_stats.sort(key=lambda r: r.transit_count, reverse=True)
    return route_stats, activity
