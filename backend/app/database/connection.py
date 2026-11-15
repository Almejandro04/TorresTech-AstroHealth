"""SQLite connection, schema, and transactions (standard-library sqlite3)."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import database_path
from app.models.fields import compare_timestamps

# An application marker AND the complete schema identify resettable databases.
APPLICATION_ID = 0x41535452  # ASTR

# Exact timestamp collation preserves fractions of arbitrary length in SQL.
# Missing measurements are SQL NULL, never 0.
SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id     TEXT PRIMARY KEY,
    source_type   TEXT NOT NULL,
    description   TEXT,
    manifest_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS astronauts (
    astronaut_id          TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    is_fictional          INTEGER NOT NULL CHECK (is_fictional = 1),
    mission_start_date    TEXT NOT NULL,
    planned_duration_days INTEGER NOT NULL CHECK (planned_duration_days > 0)
);

CREATE TABLE IF NOT EXISTS readings (
    seq                  INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id         TEXT NOT NULL REFERENCES astronauts (astronaut_id),
    timestamp            TEXT NOT NULL COLLATE ASTROHEALTH_TIMESTAMP,
    mission_day          INTEGER NOT NULL CHECK (mission_day >= 1),
    heart_rate_bpm       REAL,
    spo2_percent         REAL,
    respiratory_rate_bpm REAL,
    measurement_context  TEXT NOT NULL
        CHECK (measurement_context IN ('rest', 'exercise', 'sleep', 'unknown')),
    source_type          TEXT NOT NULL,
    source_id            TEXT NOT NULL REFERENCES sources (source_id),
    UNIQUE (astronaut_id, timestamp, measurement_context),
    CHECK (heart_rate_bpm IS NOT NULL OR spo2_percent IS NOT NULL
           OR respiratory_rate_bpm IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS journal (
    seq                    INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id           TEXT NOT NULL REFERENCES astronauts (astronaut_id),
    timestamp              TEXT NOT NULL COLLATE ASTROHEALTH_TIMESTAMP,
    mission_day            INTEGER NOT NULL CHECK (mission_day >= 1),
    sleep_hours_last_night REAL,
    mood_score             INTEGER,
    notes                  TEXT,
    source_type            TEXT NOT NULL,
    source_id              TEXT NOT NULL REFERENCES sources (source_id),
    UNIQUE (astronaut_id, mission_day),
    CHECK (sleep_hours_last_night IS NOT NULL OR mood_score IS NOT NULL
           OR notes IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS alerts (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    astronaut_id   TEXT NOT NULL REFERENCES astronauts (astronaut_id),
    timestamp      TEXT NOT NULL COLLATE ASTROHEALTH_TIMESTAMP,
    mission_day    INTEGER NOT NULL CHECK (mission_day >= 1),
    indicator      TEXT NOT NULL,
    severity       TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    status         TEXT NOT NULL CHECK (status IN ('active', 'resolved')),
    description    TEXT NOT NULL,
    explanation    TEXT NOT NULL,
    rule_id        TEXT NOT NULL,
    rule_version   TEXT NOT NULL,
    observed_value REAL NOT NULL,
    baseline_value REAL,
    unit           TEXT NOT NULL,
    window_start   TEXT NOT NULL COLLATE ASTROHEALTH_TIMESTAMP,
    window_end     TEXT NOT NULL COLLATE ASTROHEALTH_TIMESTAMP,
    resolved_at    TEXT COLLATE ASTROHEALTH_TIMESTAMP,
    source_type    TEXT NOT NULL,
    source_id      TEXT NOT NULL REFERENCES sources (source_id),
    UNIQUE (astronaut_id, rule_id, rule_version, indicator, timestamp),
    CHECK ((status = 'active') = (resolved_at IS NULL))
);
"""


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the configured database (or `path`) with foreign keys enforced.

    The caller closes the connection. Transactions are explicit; see
    `transaction`.
    """
    target = Path(path) if path is not None else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.create_collation("ASTROHEALTH_TIMESTAMP", compare_timestamps)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the tables if they do not exist. Safe to run repeatedly."""
    existing = schema_signature(conn)
    if existing and (existing != expected_schema() or
                     conn.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID):
        raise ValueError("Not an identified AstroHealth database; existing schema was not changed.")
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")


def schema_signature(conn: sqlite3.Connection) -> list[tuple]:
    return [tuple(row) for row in conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    )]


def expected_schema() -> list[tuple]:
    from contextlib import closing

    with closing(sqlite3.connect(":memory:")) as reference:
        reference.create_collation("ASTROHEALTH_TIMESTAMP", compare_timestamps)
        reference.executescript(SCHEMA)
        return schema_signature(reference)


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """Run a block atomically. Nested use joins the outer transaction.

    Any exception rolls back everything the block wrote.
    """
    if conn.in_transaction:
        conn.execute("SAVEPOINT nested")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK TO nested")
            conn.execute("RELEASE nested")
            raise
        conn.execute("RELEASE nested")
        return

    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
