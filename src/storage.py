import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .parser import StrikeEvent

DB_PATH = Path(__file__).parent.parent / "data" / "events.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                lat         REAL NOT NULL,
                lon         REAL NOT NULL,
                label       TEXT,
                source      TEXT,
                added_at    TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_events_ts_coord
                ON events(timestamp, lat, lon);

            CREATE TABLE IF NOT EXISTS ingest_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                added_at    TEXT NOT NULL,
                count       INTEGER NOT NULL,
                source      TEXT
            );
        """)


def save_events(events: List[StrikeEvent], source: Optional[str] = None) -> int:
    """Insert new events (skip duplicates). Returns count of newly added rows."""
    init_db()
    now = datetime.utcnow().isoformat()
    added = 0
    with _connect() as conn:
        for e in events:
            try:
                conn.execute(
                    "INSERT INTO events(timestamp, lat, lon, label, source, added_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (e.timestamp.isoformat(), e.lat, e.lon, e.label, source, now),
                )
                added += 1
            except sqlite3.IntegrityError:
                pass
        if added:
            conn.execute(
                "INSERT INTO ingest_log(added_at, count, source) VALUES (?, ?, ?)",
                (now, added, source),
            )
    return added


def load_events(since: Optional[datetime] = None) -> List[StrikeEvent]:
    init_db()
    with _connect() as conn:
        if since:
            rows = conn.execute(
                "SELECT timestamp, lat, lon, label FROM events WHERE timestamp >= ? ORDER BY timestamp",
                (since.isoformat(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT timestamp, lat, lon, label FROM events ORDER BY timestamp"
            ).fetchall()

    return [
        StrikeEvent(
            timestamp=datetime.fromisoformat(r["timestamp"]),
            lat=r["lat"],
            lon=r["lon"],
            label=r["label"],
        )
        for r in rows
    ]


def event_count() -> int:
    init_db()
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
