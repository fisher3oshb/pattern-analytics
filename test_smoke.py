from datetime import datetime
from src.predictor import PatternAnalyzer

# Два кластери, маршрут A→B, повторні удари з різним часом доби
SAMPLE = """
2024-03-01 06:00  48.3794, 31.1656
2024-03-01 08:30  48.5512, 31.2891
2024-03-01 14:05  48.3810, 31.1670
2024-03-01 16:20  48.5500, 31.2900
2024-03-02 06:10  48.3780, 31.1640
2024-03-02 08:45  48.5520, 31.2880
2024-03-03 05:55  48.3800, 31.1660
2024-03-03 08:20  48.5510, 31.2870
"""

a = PatternAnalyzer(radius_km=3.0, min_samples=2)
a.load(SAMPLE).fit()

print(a.full_report(from_time=datetime(2024, 3, 4, 0, 0)))
