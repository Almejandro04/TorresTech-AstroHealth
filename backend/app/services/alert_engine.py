"""Deterministic evaluation of the alert rule over the persisted history.

The evaluator walks resting heart-rate readings in (timestamp, ID) order. Each
event uses only observations with a timestamp at or before its own detection,
so the stored alerts do not depend on when the evaluation runs. Alerts are
persisted with the repository's event-key upsert: re-running never copies.
"""

import sqlite3

from app.database import repository
from app.database.connection import transaction
from app.models.fields import parse_timestamp
from app.models.schemas import Astronaut, HealthAlert, HealthAlertDraft, HealthReading
from app.services import alert_rules as rule
from app.services import analysis


def _fmt(value: float) -> str:
    return f"{round(value, 1):g}"


def evaluate(astronaut: Astronaut, readings: list[HealthReading]) -> list[HealthAlertDraft]:
    """Alert events of the rule over the full history, in detection order.

    - The reference is the #14 baseline at the reading's time; until it is
      available nothing is evaluated.
    - A day's value is the mean of its resting readings observed so far.
    - Detection: the previous mission day (after the reference window) and the
      current day both reach baseline + DELTA_BPM.
    - Resolution: a later day whose value falls below baseline + DELTA_BPM.
      A new event then needs two elevated days after the resolution day.
    """
    by_id = {r.reading_id: r for r in readings}
    series = analysis.observations_from(readings, astronaut.astronaut_id, rule.INDICATOR, rule.CONTEXT)
    series = sorted({o.record_id: o for o in series}.values(),
                    key=lambda o: (parse_timestamp(o.timestamp), o.record_id))

    drafts: list[dict] = []
    active: dict | None = None
    blocked_day = analysis.REFERENCE_LAST_DAY
    for index, item in enumerate(series):
        if item.mission_day <= analysis.REFERENCE_LAST_DAY:
            continue
        baseline = analysis.analyze_series(
            series, astronaut, rule.INDICATOR, item.timestamp, rule.CONTEXT
        ).baseline
        if baseline.status != "available":
            continue
        threshold = baseline.value + rule.DELTA_BPM
        seen = series[: index + 1]
        today = [o for o in seen if o.mission_day == item.mission_day]
        today_mean = analysis.describe([o.value for o in today]).mean

        if active is not None:
            if item.mission_day > active["mission_day"] and today_mean < threshold:
                active["status"], active["resolved_at"] = "resolved", item.timestamp
                blocked_day, active = item.mission_day, None
            continue

        previous_day = item.mission_day - (rule.CONSECUTIVE_DAYS - 1)
        if previous_day <= blocked_day:
            continue
        before = [o for o in seen if o.mission_day == previous_day]
        if not before or analysis.describe([o.value for o in before]).mean < threshold:
            continue
        if today_mean < threshold:
            continue

        window = before + today
        observed = analysis.describe([o.value for o in window]).mean
        source = by_id[item.record_id]
        active = {
            "astronaut_id": astronaut.astronaut_id,
            "timestamp": item.timestamp,
            "mission_day": item.mission_day,
            "indicator": rule.INDICATOR,
            "severity": rule.SEVERITY,
            "status": "active",
            "description": rule.DESCRIPTION,
            "explanation": rule.EXPLANATION.format(
                first_day=previous_day, last_day=item.mission_day, observed=_fmt(observed),
                ref_first=analysis.REFERENCE_FIRST_DAY, ref_last=analysis.REFERENCE_LAST_DAY,
                baseline=_fmt(baseline.value),
            ),
            "rule_id": rule.RULE_ID,
            "rule_version": rule.RULE_VERSION,
            "observed_value": observed,
            "baseline_value": baseline.value,
            "unit": rule.UNIT,
            "window_start": window[0].timestamp,
            "window_end": item.timestamp,
            "resolved_at": None,
            "source_type": source.source_type,
            "source_id": source.source_id,
        }
        drafts.append(active)
    return [HealthAlertDraft.model_validate(draft) for draft in drafts]


def evaluate_and_store(conn: sqlite3.Connection, astronaut: Astronaut) -> list[HealthAlert]:
    """Evaluate, upsert every event, and return the current events newest first.

    Stored alerts whose event no longer results from the history (for example
    after a late import inside the window) are not returned.
    """
    with transaction(conn):
        drafts = evaluate(astronaut, repository.list_readings(conn, astronaut.astronaut_id))
        ids = {repository.save_alert(conn, draft).record.alert_id for draft in drafts}
    return [a for a in repository.list_alerts(conn, astronaut.astronaut_id) if a.alert_id in ids]
