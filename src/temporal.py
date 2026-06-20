from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import numpy as np

from .clustering import Cluster


@dataclass
class TemporalPattern:
    cluster_id: int
    timestamps: List[datetime]
    avg_interval_sec: Optional[float]   # average gap between visits
    std_interval_sec: Optional[float]
    period_sec: Optional[float]         # dominant cycle length (if detected)

    @property
    def avg_interval(self) -> Optional[timedelta]:
        if self.avg_interval_sec is None:
            return None
        return timedelta(seconds=self.avg_interval_sec)

    @property
    def period(self) -> Optional[timedelta]:
        if self.period_sec is None:
            return None
        return timedelta(seconds=self.period_sec)


def _dominant_period(intervals_sec: np.ndarray) -> Optional[float]:
    if len(intervals_sec) < 4:
        return None
    # FFT on interval series to find dominant frequency
    fft = np.abs(np.fft.rfft(intervals_sec - intervals_sec.mean()))
    freqs = np.fft.rfftfreq(len(intervals_sec))
    if freqs[1:].size == 0:
        return None
    dominant_idx = np.argmax(fft[1:]) + 1
    dominant_freq = freqs[dominant_idx]
    if dominant_freq == 0:
        return None
    return float(1.0 / dominant_freq)  # in units of "number of intervals"


def analyze_temporal_patterns(clusters: List[Cluster]) -> List[TemporalPattern]:
    patterns = []

    for c in clusters:
        times = sorted(e.timestamp for e in c.events)

        if len(times) < 2:
            patterns.append(TemporalPattern(
                cluster_id=c.id,
                timestamps=times,
                avg_interval_sec=None,
                std_interval_sec=None,
                period_sec=None,
            ))
            continue

        intervals = np.array([
            (times[i + 1] - times[i]).total_seconds()
            for i in range(len(times) - 1)
        ])

        avg = float(intervals.mean())
        std = float(intervals.std())
        period = _dominant_period(intervals)
        # Convert FFT period from "interval units" back to seconds
        period_sec = period * avg if period is not None else None

        patterns.append(TemporalPattern(
            cluster_id=c.id,
            timestamps=times,
            avg_interval_sec=avg,
            std_interval_sec=std,
            period_sec=period_sec,
        ))

    return patterns
