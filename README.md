# pattern-analytics

Algorithm for predicting target locations based on historical strike time and position data.

## Concept

Given a dataset of `(timestamp, lat, lon)` strike events, the system:

1. **Clusters** known strike locations to identify hotspots
2. **Infers routes** between clusters using temporal sequences
3. **Detects time patterns** (intervals, periodicity) per location and route
4. **Predicts** when and where to search next

## Project Structure

```
src/
  clustering.py   — spatial clustering of strike points (DBSCAN)
  routes.py       — route graph inference between clusters
  temporal.py     — time-series pattern detection
  predictor.py    — prediction engine combining all modules
data/             — input data (not committed)
notebooks/        — exploration and visualization
```

## Setup

```bash
pip install -r requirements.txt
```

## Input Format

CSV with columns: `timestamp` (ISO 8601), `lat`, `lon`

```csv
timestamp,lat,lon
2024-03-01T06:15:00,48.3794,31.1656
2024-03-01T08:42:00,48.5512,31.2891
```
