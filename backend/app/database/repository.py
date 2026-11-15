"""Persistence operations. No HTTP, filtering, pagination, or analysis here.

Record IDs are generated from each table's AUTOINCREMENT sequence
(`READING-0001`, `JOURNAL-0001`, `ALERT-0001`); a sequence value is never
reused. Ordering by ID uses the numeric sequence.
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from pydantic import ValidationError

from app.database.connection import transaction
from app.models.fields import canonical_timestamp, storage_timestamp
from app.models.schemas import (
    Astronaut,
    HealthAlert,
    HealthAlertDraft,
    HealthJournal,
    HealthJournalInput,
    HealthReading,
    HealthReadingInput,
    SourceManifestEntry,
)
from app.models.validation import (
    AlertNotFoundError,
    AstronautNotFoundError,
    FieldIssue,
    RecordValidationError,
    issues_from_pydantic,
    mission_day_issues,
)

RecordT = TypeVar("RecordT")


@dataclass(frozen=True)
class WriteResult(Generic[RecordT]):
    """Outcome of a write and the record now stored under that key."""

    status: str
    record: RecordT


ReadingStatus = Literal["created", "existing", "conflict"]
UpsertStatus = Literal["created", "updated"]


def _record_id(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:04d}"


def _seq_from_id(prefix: str, record_id: str) -> int | None:
    head, _, digits = record_id.partition("-")
    if head != prefix or not digits.isascii() or not digits.isdigit():
        return None
    return int(digits)


# --- row mapping -----------------------------------------------------------


def _astronaut(row: sqlite3.Row) -> Astronaut:
    return Astronaut(
        astronaut_id=row["astronaut_id"],
        name=row["name"],
        is_fictional=bool(row["is_fictional"]),
        mission_start_date=row["mission_start_date"],
        planned_duration_days=row["planned_duration_days"],
    )


def _reading(row: sqlite3.Row) -> HealthReading:
    return HealthReading(
        reading_id=_record_id("READING", row["seq"]),
        astronaut_id=row["astronaut_id"],
        timestamp=canonical_timestamp(row["timestamp"]),
        mission_day=row["mission_day"],
        heart_rate_bpm=row["heart_rate_bpm"],
        spo2_percent=row["spo2_percent"],
        respiratory_rate_bpm=row["respiratory_rate_bpm"],
        measurement_context=row["measurement_context"],
        source_type=row["source_type"],
        source_id=row["source_id"],
    )


def _journal(row: sqlite3.Row) -> HealthJournal:
    return HealthJournal(
        journal_id=_record_id("JOURNAL", row["seq"]),
        astronaut_id=row["astronaut_id"],
        timestamp=canonical_timestamp(row["timestamp"]),
        mission_day=row["mission_day"],
        sleep_hours_last_night=row["sleep_hours_last_night"],
        mood_score=row["mood_score"],
        notes=row["notes"],
        source_type=row["source_type"],
        source_id=row["source_id"],
    )


def _alert(row: sqlite3.Row) -> HealthAlert:
    resolved_at = row["resolved_at"]
    return HealthAlert(
        alert_id=_record_id("ALERT", row["seq"]),
        astronaut_id=row["astronaut_id"],
        timestamp=canonical_timestamp(row["timestamp"]),
        mission_day=row["mission_day"],
        indicator=row["indicator"],
        severity=row["severity"],
        status=row["status"],
        description=row["description"],
        explanation=row["explanation"],
        rule_id=row["rule_id"],
        rule_version=row["rule_version"],
        observed_value=row["observed_value"],
        baseline_value=row["baseline_value"],
        unit=row["unit"],
        window_start=canonical_timestamp(row["window_start"]),
        window_end=canonical_timestamp(row["window_end"]),
        resolved_at=None if resolved_at is None else canonical_timestamp(resolved_at),
        source_type=row["source_type"],
        source_id=row["source_id"],
    )


# --- profile-dependent validation -------------------------------------------


def _source_issues(
    conn: sqlite3.Connection, source_id: str, source_type: str, prefix: str
) -> list[FieldIssue]:
    row = conn.execute(
        "SELECT source_type FROM sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    if row is None:
        return [
            {
                "field": f"{prefix}.source_id",
                "message": "Is not a known source in the manifest.",
            }
        ]
    if row["source_type"] != source_type:
        return [
            {
                "field": f"{prefix}.source_type",
                "message": "Does not match the source manifest.",
            }
        ]
    return []


def _check_record(
    conn: sqlite3.Connection,
    astronaut_id: str,
    timestamp: str,
    mission_day: int,
    source_id: str,
    source_type: str,
    prefix: str,
) -> None:
    """Raise unless the astronaut, mission day, and source are all valid."""
    astronaut = require_astronaut(conn, astronaut_id)
    issues = mission_day_issues(astronaut, timestamp, mission_day, prefix)
    issues += _source_issues(conn, source_id, source_type, prefix)
    if issues:
        raise RecordValidationError(issues)


# --- sources and astronauts ---------------------------------------------------


def save_source(conn: sqlite3.Connection, source: SourceManifestEntry) -> None:
    """Insert or replace a manifest entry, keeping all of its fields."""
    with transaction(conn):
        conn.execute(
            """
            INSERT INTO sources (source_id, source_type, description, manifest_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (source_id) DO UPDATE SET
                source_type = excluded.source_type,
                description = excluded.description,
                manifest_json = excluded.manifest_json
            """,
            (
                source.source_id,
                source.source_type,
                source.description,
                json.dumps(source.model_dump(), sort_keys=True),
            ),
        )


def save_astronaut(conn: sqlite3.Connection, astronaut: Astronaut) -> None:
    """Insert or update a seeded profile."""
    with transaction(conn):
        conn.execute(
            """
            INSERT INTO astronauts (astronaut_id, name, is_fictional,
                                    mission_start_date, planned_duration_days)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (astronaut_id) DO UPDATE SET
                name = excluded.name,
                is_fictional = excluded.is_fictional,
                mission_start_date = excluded.mission_start_date,
                planned_duration_days = excluded.planned_duration_days
            """,
            (
                astronaut.astronaut_id,
                astronaut.name,
                int(astronaut.is_fictional),
                astronaut.mission_start_date,
                astronaut.planned_duration_days,
            ),
        )


def list_astronauts(conn: sqlite3.Connection) -> list[Astronaut]:
    rows = conn.execute("SELECT * FROM astronauts ORDER BY astronaut_id").fetchall()
    return [_astronaut(row) for row in rows]


def get_astronaut(conn: sqlite3.Connection, astronaut_id: str) -> Astronaut | None:
    row = conn.execute(
        "SELECT * FROM astronauts WHERE astronaut_id = ?", (astronaut_id,)
    ).fetchone()
    return None if row is None else _astronaut(row)


def require_astronaut(conn: sqlite3.Connection, astronaut_id: str) -> Astronaut:
    astronaut = get_astronaut(conn, astronaut_id)
    if astronaut is None:
        raise AstronautNotFoundError(astronaut_id)
    return astronaut


# --- readings -----------------------------------------------------------------


def create_reading(
    conn: sqlite3.Connection,
    astronaut_id: str,
    payload: HealthReadingInput,
    *,
    field_prefix: str = "body",
) -> WriteResult[HealthReading]:
    """Store a reading keyed by (astronaut, timestamp, measurement_context).

    `created`: new row. `existing`: the same key with identical values, so the
    stored record is returned and nothing is written. `conflict`: the same key
    with different values or provenance; the stored record is returned
    unchanged.
    """
    with transaction(conn):
        _check_record(
            conn,
            astronaut_id,
            payload.timestamp,
            payload.mission_day,
            payload.source_id,
            payload.source_type,
            field_prefix,
        )
        stored_timestamp = storage_timestamp(payload.timestamp)
        row = conn.execute(
            """
            SELECT * FROM readings
            WHERE astronaut_id = ? AND timestamp = ? AND measurement_context = ?
            """,
            (astronaut_id, stored_timestamp, payload.measurement_context),
        ).fetchone()
        if row is not None:
            existing = _reading(row)
            same = (
                existing.model_dump(exclude={"reading_id", "astronaut_id"})
                == payload.model_dump()
            )
            return WriteResult("existing" if same else "conflict", existing)

        cursor = conn.execute(
            """
            INSERT INTO readings (astronaut_id, timestamp, mission_day,
                                  heart_rate_bpm, spo2_percent, respiratory_rate_bpm,
                                  measurement_context, source_type, source_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                astronaut_id,
                stored_timestamp,
                payload.mission_day,
                payload.heart_rate_bpm,
                payload.spo2_percent,
                payload.respiratory_rate_bpm,
                payload.measurement_context,
                payload.source_type,
                payload.source_id,
            ),
        )
        created = conn.execute(
            "SELECT * FROM readings WHERE seq = ?", (cursor.lastrowid,)
        ).fetchone()
        return WriteResult("created", _reading(created))


def list_readings(conn: sqlite3.Connection, astronaut_id: str) -> list[HealthReading]:
    """All readings of a known astronaut, by (timestamp, ID) ascending."""
    require_astronaut(conn, astronaut_id)
    rows = conn.execute(
        "SELECT * FROM readings WHERE astronaut_id = ? ORDER BY timestamp, seq",
        (astronaut_id,),
    ).fetchall()
    return [_reading(row) for row in rows]


# --- journal ------------------------------------------------------------------


def upsert_journal(
    conn: sqlite3.Connection,
    astronaut_id: str,
    payload: HealthJournalInput,
    *,
    field_prefix: str = "body",
) -> WriteResult[HealthJournal]:
    """Create or replace the single entry of (astronaut, mission_day).

    An update keeps the `journal_id`. Because the day must match the
    timestamp, an entry cannot move to another day.
    """
    with transaction(conn):
        _check_record(
            conn,
            astronaut_id,
            payload.timestamp,
            payload.mission_day,
            payload.source_id,
            payload.source_type,
            field_prefix,
        )
        values = (
            storage_timestamp(payload.timestamp),
            payload.sleep_hours_last_night,
            payload.mood_score,
            payload.notes,
            payload.source_type,
            payload.source_id,
        )
        key = (astronaut_id, payload.mission_day)
        existing = conn.execute(
            "SELECT seq FROM journal WHERE astronaut_id = ? AND mission_day = ?", key
        ).fetchone()
        if existing is None:
            status = "created"
            conn.execute(
                """
                INSERT INTO journal (timestamp, sleep_hours_last_night, mood_score,
                                     notes, source_type, source_id,
                                     astronaut_id, mission_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values + key,
            )
        else:
            status = "updated"
            conn.execute(
                """
                UPDATE journal
                SET timestamp = ?, sleep_hours_last_night = ?, mood_score = ?,
                    notes = ?, source_type = ?, source_id = ?
                WHERE astronaut_id = ? AND mission_day = ?
                """,
                values + key,
            )
        row = conn.execute(
            "SELECT * FROM journal WHERE astronaut_id = ? AND mission_day = ?", key
        ).fetchone()
        return WriteResult(status, _journal(row))


def list_journal(conn: sqlite3.Connection, astronaut_id: str) -> list[HealthJournal]:
    """All journal entries of a known astronaut, by (timestamp, ID) ascending."""
    require_astronaut(conn, astronaut_id)
    rows = conn.execute(
        "SELECT * FROM journal WHERE astronaut_id = ? ORDER BY timestamp, seq",
        (astronaut_id,),
    ).fetchall()
    return [_journal(row) for row in rows]


# --- alerts -------------------------------------------------------------------

_ALERT_KEY = "astronaut_id = ? AND rule_id = ? AND rule_version = ? AND indicator = ? AND timestamp = ?"


def save_alert(
    conn: sqlite3.Connection, draft: HealthAlertDraft, *, field_prefix: str = "alert"
) -> WriteResult[HealthAlert]:
    """Store one alert per event key, without creating copies.

    Event key: (astronaut_id, rule_id, rule_version, indicator, timestamp).
    Saving the same event again keeps its `alert_id` and replaces the other
    fields, which is how a later evaluation marks it resolved.
    """
    with transaction(conn):
        _check_record(
            conn,
            draft.astronaut_id,
            draft.timestamp,
            draft.mission_day,
            draft.source_id,
            draft.source_type,
            field_prefix,
        )
        key = (
            draft.astronaut_id,
            draft.rule_id,
            draft.rule_version,
            draft.indicator,
            storage_timestamp(draft.timestamp),
        )
        values = (
            draft.mission_day,
            draft.severity,
            draft.status,
            draft.description,
            draft.explanation,
            draft.observed_value,
            draft.baseline_value,
            draft.unit,
            storage_timestamp(draft.window_start),
            storage_timestamp(draft.window_end),
            None if draft.resolved_at is None else storage_timestamp(draft.resolved_at),
            draft.source_type,
            draft.source_id,
        )
        existing = conn.execute(
            f"SELECT seq FROM alerts WHERE {_ALERT_KEY}", key
        ).fetchone()
        if existing is None:
            status = "created"
            conn.execute(
                """
                INSERT INTO alerts (mission_day, severity, status, description,
                                    explanation, observed_value, baseline_value, unit,
                                    window_start, window_end, resolved_at,
                                    source_type, source_id,
                                    astronaut_id, rule_id, rule_version, indicator,
                                    timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values + key,
            )
        else:
            status = "updated"
            conn.execute(
                f"""
                UPDATE alerts
                SET mission_day = ?, severity = ?, status = ?, description = ?,
                    explanation = ?, observed_value = ?, baseline_value = ?, unit = ?,
                    window_start = ?, window_end = ?, resolved_at = ?,
                    source_type = ?, source_id = ?
                WHERE {_ALERT_KEY}
                """,
                values + key,
            )
        row = conn.execute(f"SELECT * FROM alerts WHERE {_ALERT_KEY}", key).fetchone()
        return WriteResult(status, _alert(row))


def resolve_alert(conn: sqlite3.Connection, alert_id: str, resolved_at: str) -> HealthAlert:
    """Mark a stored alert resolved at `resolved_at` (not before detection)."""
    with transaction(conn):
        seq = _seq_from_id("ALERT", alert_id)
        row = (
            None
            if seq is None
            else conn.execute("SELECT * FROM alerts WHERE seq = ?", (seq,)).fetchone()
        )
        if row is None:
            raise AlertNotFoundError(alert_id)
        try:
            resolved = HealthAlert.model_validate(
                {**_alert(row).model_dump(), "status": "resolved", "resolved_at": resolved_at}
            )
        except ValidationError as error:
            raise RecordValidationError(issues_from_pydantic(error, "alert")) from None
        conn.execute(
            "UPDATE alerts SET status = 'resolved', resolved_at = ? WHERE seq = ?",
            (storage_timestamp(resolved.resolved_at), seq),
        )
        return resolved


def list_alerts(conn: sqlite3.Connection, astronaut_id: str) -> list[HealthAlert]:
    """All alerts of a known astronaut, newest first, then by ID ascending."""
    require_astronaut(conn, astronaut_id)
    rows = conn.execute(
        "SELECT * FROM alerts WHERE astronaut_id = ? ORDER BY timestamp DESC, seq",
        (astronaut_id,),
    ).fetchall()
    return [_alert(row) for row in rows]


def count_records(conn: sqlite3.Connection) -> dict[str, int]:
    """Row counts per table, for init/seed/reset reports."""
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("sources", "astronauts", "readings", "journal", "alerts")
    }
