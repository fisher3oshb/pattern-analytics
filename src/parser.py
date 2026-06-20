import re
import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class StrikeEvent:
    timestamp: datetime
    lat: float
    lon: float
    label: Optional[str] = None


# Patterns for free-text parsing
_DATE_PATTERNS = [
    r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)',   # ISO: 2024-03-01T06:15
    r'(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}(?::\d{2})?)',   # UA:  01.03.2024 06:15
    r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)',     # US:  03/01/2024 06:15
]

_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
    '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M',
    '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M',
]

_COORD_PATTERN = re.compile(
    r'(\d{2,3}\.\d+)[,\s]+(\d{2,3}\.\d+)'
)


def _parse_datetime(s: str) -> Optional[datetime]:
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_text(text: str) -> List[StrikeEvent]:
    events = []
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    for line in lines:
        ts = None
        for pat in _DATE_PATTERNS:
            m = re.search(pat, line)
            if m:
                ts = _parse_datetime(m.group(1))
                break

        coords = _COORD_PATTERN.search(line)
        if ts and coords:
            lat, lon = float(coords.group(1)), float(coords.group(2))
            events.append(StrikeEvent(timestamp=ts, lat=lat, lon=lon))

    return events


def _parse_table(text: str) -> List[StrikeEvent]:
    events = []
    reader = csv.DictReader(io.StringIO(text.strip()))

    # Flexible column name mapping
    col_map = {}
    for field in reader.fieldnames or []:
        key = field.strip().lower()
        if key in ('timestamp', 'time', 'datetime', 'date', 'час', 'дата'):
            col_map['timestamp'] = field
        elif key in ('lat', 'latitude', 'широта'):
            col_map['lat'] = field
        elif key in ('lon', 'lng', 'longitude', 'довгота'):
            col_map['lon'] = field
        elif key in ('label', 'name', 'note', 'ціль', 'мітка'):
            col_map['label'] = field

    if not all(k in col_map for k in ('timestamp', 'lat', 'lon')):
        raise ValueError(f"Table must have timestamp, lat, lon columns. Found: {reader.fieldnames}")

    for row in reader:
        ts = _parse_datetime(row[col_map['timestamp']])
        if ts is None:
            continue
        lat = float(row[col_map['lat']])
        lon = float(row[col_map['lon']])
        label = row.get(col_map.get('label', ''), None)
        events.append(StrikeEvent(timestamp=ts, lat=lat, lon=lon, label=label))

    return events


def parse(text: str) -> List[StrikeEvent]:
    """
    Auto-detect format (CSV table or free text) and return list of StrikeEvent.
    """
    stripped = text.strip()
    first_line = stripped.splitlines()[0] if stripped else ''

    # Heuristic: if first line has commas and no coordinates → likely CSV header
    if ',' in first_line and not _COORD_PATTERN.search(first_line):
        try:
            events = _parse_table(stripped)
            if events:
                return events
        except (ValueError, KeyError):
            pass

    return _parse_text(stripped)
