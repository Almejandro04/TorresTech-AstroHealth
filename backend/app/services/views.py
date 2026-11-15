"""Read views over stored records: observation cutoff, day filters, summary.

`as_of` is an observation-time cutoff. Nothing observed after it may appear in
or influence a response. Baselines (#14) and alert evaluation (#15) are not
implemented; their explicit `not_implemented` states are produced here so the
response schemas stay stable when those issues replace them.
"""

import sqlite3
from typing import TypeVar

from app.database import repository
from app.models.fields import (
    INDICATOR_UNITS,
    canonical_timestamp,
    mission_day_for,
    parse_timestamp,
)
from app.models.responses import (
    AlertSummary,
    BaselineMetric,
    Baselines,
    EvaluationStatus,
    HealthSummary,
    LatestMetrics,
    MetricSnapshot,
)
from app.models.schemas import Astronaut, HealthAlert, HealthJournal, HealthReading
from app.models.validation import FieldIssue, RecordValidationError

RecordT = TypeVar("RecordT", HealthReading, HealthJournal, HealthAlert)

VITAL_INDICATORS = ("heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm")
JOURNAL_INDICATORS = ("sleep_hours_last_night", "mood_score")


def _query_issue(name: str, message: str) -> FieldIssue:
    return {"field": f"query.{name}", "message": message}


# --- cutoff and filters -------------------------------------------------------


def resolve_as_of(
    conn: sqlite3.Connection, astronaut: Astronaut, requested: str | None
) -> str | None:
    """Return the effective cutoff in canonical form.

    An explicit value must be a UTC timestamp inside the mission. Without one,
    the cutoff is the latest stored reading or journal timestamp of the
    profile, or None when it has no observations.
    """
    if requested is None:
        stamps = [r.timestamp for r in repository.list_readings(conn, astronaut.astronaut_id)]
        stamps += [j.timestamp for j in repository.list_journal(conn, astronaut.astronaut_id)]
        return max(stamps, key=parse_timestamp, default=None)

    try:
        as_of = canonical_timestamp(requested)
    except ValueError:
        raise RecordValidationError(
            [_query_issue("as_of", "Must be a UTC timestamp ending in Z, such as 2026-11-07T12:00:00Z.")]
        ) from None
    day = mission_day_for(as_of, astronaut.mission_start_date)
    if not 1 <= day <= astronaut.planned_duration_days:
        raise RecordValidationError([_query_issue("as_of", "Must be within the mission.")])
    return as_of


def check_day_range(astronaut: Astronaut, from_day: int | None, to_day: int | None) -> None:
    """Reject bounds outside the mission or reversed."""
    issues = [
        _query_issue(name, "Must be within the planned mission duration.")
        for name, value in (("from_day", from_day), ("to_day", to_day))
        if value is not None and not 1 <= value <= astronaut.planned_duration_days
    ]
    if not issues and from_day is not None and to_day is not None and from_day > to_day:
        issues.append(_query_issue("to_day", "Must not be earlier than from_day."))
    if issues:
        raise RecordValidationError(issues)


def visible(
    records: list[RecordT],
    as_of: str | None,
    from_day: int | None = None,
    to_day: int | None = None,
) -> list[RecordT]:
    """Keep records observed at or before the cutoff and inside the day bounds."""
    if as_of is None:
        return []
    cutoff = parse_timestamp(as_of)
    return [
        record
        for record in records
        if parse_timestamp(record.timestamp) <= cutoff
        and (from_day is None or record.mission_day >= from_day)
        and (to_day is None or record.mission_day <= to_day)
    ]


def page(items: list[RecordT], limit: int, offset: int) -> list[RecordT]:
    return items[offset : offset + limit]


# --- analysis placeholders ----------------------------------------------------


def alert_view(
    conn: sqlite3.Connection, astronaut: Astronaut, as_of: str | None
) -> tuple[EvaluationStatus, list[HealthAlert]]:
    """Alert evaluation as seen at `as_of`: its status and its alerts.

    The alert engine (#15) replaces this body. Until then the evaluation is
    reported as not implemented, and no alerts are returned, so that an empty
    list is never read as a completed evaluation.
    """
    return "not_implemented", []


def _baselines() -> Baselines:
    """Explicit placeholders until baselines are calculated (#14)."""

    def pending() -> BaselineMetric:
        return BaselineMetric(
            status="not_implemented",
            value=None,
            sample_count=0,
            reference_start=None,
            reference_end=None,
            measurement_context=None,
            method=None,
        )

    return Baselines(
        heart_rate_bpm=pending(),
        spo2_percent=pending(),
        respiratory_rate_bpm=pending(),
        sleep_hours_last_night=pending(),
    )


_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def _alert_summary(status: EvaluationStatus, alerts: list[HealthAlert]) -> AlertSummary:
    if status != "available":
        return AlertSummary(
            evaluation_status=status, active_count=None, highest_severity=None, recent=[]
        )
    active = [alert for alert in alerts if alert.status == "active"]
    highest = max((a.severity for a in active), key=_SEVERITY_ORDER.__getitem__, default=None)
    return AlertSummary(
        evaluation_status=status,
        active_count=len(active),
        highest_severity=highest,
        recent=active[:3],
    )


# --- summary ------------------------------------------------------------------


def _snapshot(indicator: str, records: list, id_field: str) -> MetricSnapshot:
    """Latest non-null value of `indicator`; records are in (timestamp, ID) order."""
    for record in reversed(records):
        value = getattr(record, indicator)
        if value is not None:
            return MetricSnapshot(
                value=value,
                unit=INDICATOR_UNITS[indicator],
                timestamp=record.timestamp,
                mission_day=record.mission_day,
                measurement_context=getattr(record, "measurement_context", None),
                source_type=record.source_type,
                source_id=record.source_id,
                record_id=getattr(record, id_field),
            )
    return MetricSnapshot(
        value=None,
        unit=INDICATOR_UNITS[indicator],
        timestamp=None,
        mission_day=None,
        measurement_context=None,
        source_type=None,
        source_id=None,
        record_id=None,
    )


def build_summary(
    conn: sqlite3.Connection, astronaut: Astronaut, as_of: str | None
) -> HealthSummary:
    """Dashboard summary at the cutoff. Each indicator is selected on its own."""
    readings = visible(repository.list_readings(conn, astronaut.astronaut_id), as_of)
    journal = visible(repository.list_journal(conn, astronaut.astronaut_id), as_of)
    snapshots = {name: _snapshot(name, readings, "reading_id") for name in VITAL_INDICATORS}
    snapshots |= {name: _snapshot(name, journal, "journal_id") for name in JOURNAL_INDICATORS}

    return HealthSummary(
        astronaut=astronaut,
        mission_day=None if as_of is None else mission_day_for(as_of, astronaut.mission_start_date),
        latest_reading=readings[-1] if readings else None,
        latest_journal=journal[-1] if journal else None,
        latest_metrics=LatestMetrics(**snapshots),
        baselines=_baselines(),
        alert_summary=_alert_summary(*alert_view(conn, astronaut, as_of)),
    )
