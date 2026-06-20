from src.predictor import PatternAnalyzer

# Two clusters, A visited 3 times, B visited 2 times, with a route A→B between them
SAMPLE = """
2024-03-01 06:00  48.3794, 31.1656
2024-03-01 08:30  48.5512, 31.2891
2024-03-01 14:00  48.3810, 31.1670
2024-03-01 16:20  48.5500, 31.2900
2024-03-02 06:10  48.3780, 31.1640
2024-03-02 08:45  48.5520, 31.2880
"""

a = PatternAnalyzer(radius_km=3.0, min_samples=2)
a.load(SAMPLE).fit()

print("=== Summary ===")
print(a.summary())

print("\n=== Predictions ===")
from datetime import datetime
preds = a.predict(from_time=datetime(2024, 3, 3, 0, 0))
for p in preds:
    print(p)
    print()
