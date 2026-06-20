from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from datetime import timedelta
import networkx as nx

from .clustering import Cluster
from .parser import StrikeEvent


@dataclass
class RouteEdge:
    from_cluster: int
    to_cluster: int
    travel_times: List[float] = field(default_factory=list)  # seconds

    @property
    def avg_travel_time(self) -> float:
        return float(sum(self.travel_times) / len(self.travel_times)) if self.travel_times else 0.0

    @property
    def count(self) -> int:
        return len(self.travel_times)


def build_route_graph(
    clusters: List[Cluster],
    labels: List[int],
    events: List[StrikeEvent],
    max_gap_hours: float = 6.0,
) -> Tuple[nx.DiGraph, Dict[Tuple[int, int], RouteEdge]]:
    """
    Infer routes between clusters from temporal sequences of strike events.

    Two consecutive events (sorted by time) that belong to different clusters
    form a directed edge if the time gap is within max_gap_hours.
    """
    G = nx.DiGraph()
    edges: Dict[Tuple[int, int], RouteEdge] = {}

    for c in clusters:
        G.add_node(c.id, lat=c.center_lat, lon=c.center_lon, size=c.size)

    # Sort events by time, keep only clustered ones
    clustered = sorted(
        [(events[i], labels[i]) for i in range(len(events)) if labels[i] != -1],
        key=lambda x: x[0].timestamp,
    )

    max_gap = timedelta(hours=max_gap_hours)

    for i in range(len(clustered) - 1):
        ev_a, cl_a = clustered[i]
        ev_b, cl_b = clustered[i + 1]

        if cl_a == cl_b:
            continue
        gap = ev_b.timestamp - ev_a.timestamp
        if gap <= timedelta(0) or gap > max_gap:
            continue

        key = (cl_a, cl_b)
        if key not in edges:
            edges[key] = RouteEdge(from_cluster=cl_a, to_cluster=cl_b)
        edges[key].travel_times.append(gap.total_seconds())

    for (src, dst), edge in edges.items():
        G.add_edge(src, dst, avg_seconds=edge.avg_travel_time, count=edge.count)

    return G, edges
