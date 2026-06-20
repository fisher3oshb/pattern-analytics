import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple
from sklearn.cluster import DBSCAN

from .parser import StrikeEvent

EARTH_RADIUS_KM = 6371.0


@dataclass
class Cluster:
    id: int
    center_lat: float
    center_lon: float
    events: List[StrikeEvent] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.events)


def _haversine_matrix(coords: np.ndarray) -> np.ndarray:
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def cluster_events(
    events: List[StrikeEvent],
    radius_km: float = 5.0,
    min_samples: int = 2,
) -> Tuple[List[Cluster], List[int]]:
    """
    Cluster strike events spatially using DBSCAN.

    Returns:
        clusters: list of Cluster objects (noise points excluded)
        labels:   per-event cluster id (-1 = noise)
    """
    if not events:
        return [], []

    coords = np.array([[e.lat, e.lon] for e in events])
    dist_matrix = _haversine_matrix(coords)

    db = DBSCAN(eps=radius_km, min_samples=min_samples, metric='precomputed')
    labels = db.fit_predict(dist_matrix).tolist()

    clusters: dict[int, Cluster] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        if label not in clusters:
            clusters[label] = Cluster(id=label, center_lat=0.0, center_lon=0.0)
        clusters[label].events.append(events[idx])

    # Compute centroid for each cluster
    result = []
    for c in clusters.values():
        lats = [e.lat for e in c.events]
        lons = [e.lon for e in c.events]
        c.center_lat = float(np.mean(lats))
        c.center_lon = float(np.mean(lons))
        result.append(c)

    result.sort(key=lambda c: c.id)
    return result, labels
