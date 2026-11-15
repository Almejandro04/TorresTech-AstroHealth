"""BACKEND-02 checks: contract models accept the fixtures and reject bad shapes."""

import json
import math

import pytest
from pydantic import ValidationError

from app.config import SCHEMA_VERSION
from app.main import ResponseMeta
from app.models import (
    Astronaut,
    HealthAlert,
    HealthJournal,
    HealthJournalInput,
    HealthReading,
    HealthReadingInput,
    issues_from_pydantic,
    mission_day_issues,
)
from app.models.fields import canonical_timestamp, mission_day_for, storage_timestamp

from conftest import alert_record, api_case, journal_body, reading_body

ASTRONAUT = Astronaut(
    astronaut_id="AST-001",
    name="Demo Astronaut 1",
    is_fictional=True,
    mission_start_date="2026-11-01",
    planned_duration_days=30,
)


def rejected(model, data: dict) -> list[dict]:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(data)
    return issues_from_pydantic(caught.value)


def fields_of(issues: list[dict]) -> set[str]:
    return {issue["field"] for issue in issues}


# --- fixtures are valid -------------------------------------------------------


def test_schema_version_has_one_definition() -> None:
    assert SCHEMA_VERSION == "0.1.0"
    assert ResponseMeta(schema_version=SCHEMA_VERSION, as_of=None).schema_version == "0.1.0"
    with pytest.raises(ValidationError):
        ResponseMeta(schema_version="0.2.0", as_of=None)


def test_fixture_records_are_valid_and_round_trip() -> None:
    profiles = api_case("fictional_profiles")["response"]["body"]["data"]
    readings = api_case("readings_history_with_null_metric")["response"]["body"]["data"]
    journals = api_case("journal_history_for_sleep_chart")["response"]["body"]["data"]
    alerts = api_case("explainable_synthetic_alert")["response"]["body"]["data"]

    for model, records in (
        (Astronaut, profiles),
        (HealthReading, readings),
        (HealthJournal, journals),
        (HealthAlert, alerts),
    ):
        for record in records:
            assert model.model_validate(record).model_dump() == record

    assert HealthReadingInput.model_validate(reading_body()).model_dump() == reading_body()
    assert HealthJournalInput.model_validate(journal_body()).model_dump() == journal_body()
    assert readings[1]["respiratory_rate_bpm"] is None


def test_json_integer_is_accepted_as_number() -> None:
    from_python = HealthReadingInput.model_validate(reading_body(heart_rate_bpm=72))
    from_json = HealthReadingInput.model_validate_json(json.dumps(reading_body(heart_rate_bpm=72)))

    assert from_python.heart_rate_bpm == from_json.heart_rate_bpm == 72
    assert isinstance(from_json.heart_rate_bpm, float)


# --- strict shape rules -------------------------------------------------------


def test_unknown_field_is_rejected() -> None:
    assert fields_of(rejected(HealthReadingInput, reading_body(fatigue=3))) == {"body.fatigue"}
    assert fields_of(rejected(HealthJournalInput, journal_body(astronaut_id="AST-001"))) == {
        "body.astronaut_id"
    }


@pytest.mark.parametrize("field", sorted(reading_body()))
def test_every_reading_field_is_required_even_when_nullable(field: str) -> None:
    body = reading_body()
    del body[field]
    assert fields_of(rejected(HealthReadingInput, body)) == {f"body.{field}"}


@pytest.mark.parametrize("field", sorted(journal_body()))
def test_every_journal_field_is_required_even_when_nullable(field: str) -> None:
    body = journal_body()
    del body[field]
    assert fields_of(rejected(HealthJournalInput, body)) == {f"body.{field}"}


def test_numeric_text_is_not_a_number() -> None:
    issues = rejected(HealthReadingInput, reading_body(heart_rate_bpm="83"))
    expected = api_case("numeric_string_is_not_a_measurement")["response"]["body"]["error"]
    assert issues == expected["details"]


@pytest.mark.parametrize(
    ("model", "body"),
    [
        (HealthReadingInput, reading_body(heart_rate_bpm=True)),
        (HealthReadingInput, reading_body(spo2_percent=False)),
        (HealthReadingInput, reading_body(mission_day=True)),
        (HealthJournalInput, journal_body(mood_score=True)),
        (HealthJournalInput, journal_body(sleep_hours_last_night=True)),
    ],
)
def test_boolean_is_not_a_number_or_integer(model, body: dict) -> None:
    assert len(rejected(model, body)) == 1
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(body))


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    assert fields_of(rejected(HealthReadingInput, reading_body(heart_rate_bpm=value))) == {
        "body.heart_rate_bpm"
    }
    assert fields_of(rejected(HealthAlert, {**alert_record(), "alert_id": "ALERT-0001", "observed_value": value})) == {
        "body.observed_value"
    }


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-08T12:00:00",
        "2026-11-08T12:00:00+00:00",
        "2026-11-08T07:00:00-05:00",
        "2026-11-08T12:00Z",
        "2026-11-08 12:00:00Z",
        "2026-11-08",
        "2026-13-08T12:00:00Z",
        "",
    ],
)
def test_timestamps_must_be_utc_with_z_and_seconds(value: str) -> None:
    assert fields_of(rejected(HealthReadingInput, reading_body(timestamp=value))) == {
        "body.timestamp"
    }


def test_equivalent_timestamps_share_one_canonical_form() -> None:
    forms = ["2026-11-08T12:00:00Z", "2026-11-08T12:00:00.0Z", "2026-11-08T12:00:00.000Z"]
    assert {canonical_timestamp(form) for form in forms} == {"2026-11-08T12:00:00Z"}
    assert {storage_timestamp(form) for form in forms} == {"2026-11-08T12:00:00.000000Z"}
    assert canonical_timestamp("2026-11-08T12:00:00.250Z") == "2026-11-08T12:00:00.25Z"
    assert HealthReadingInput.model_validate(
        reading_body(timestamp="2026-11-08T12:00:00.000Z")
    ).timestamp == "2026-11-08T12:00:00Z"
    # Stored text sorts in time order even when only some values have fractions.
    assert storage_timestamp("2026-11-08T12:00:00Z") < storage_timestamp("2026-11-08T12:00:00.5Z")


def test_arbitrary_fraction_precision_is_exact() -> None:
    from app.models.fields import parse_timestamp

    prefix = "2026-11-08T12:00:00"
    fraction = "1234567" + "0" * 5000 + "1"
    assert canonical_timestamp(prefix + "." + fraction + "00Z") == prefix + "." + fraction + "Z"
    assert parse_timestamp(prefix + ".1234567Z") < parse_timestamp(prefix + ".12345671Z")
    assert parse_timestamp(prefix + ".0000000Z") == parse_timestamp(prefix + "Z")
    assert HealthReadingInput.model_validate(reading_body(timestamp=prefix + ".1234567Z")).timestamp.endswith(".1234567Z")


def test_alert_window_does_not_round_submicroseconds() -> None:
    body = alert_record(timestamp="2026-11-07T12:00:00.1234567Z",
                        window_end="2026-11-07T12:00:00.12345671Z")
    assert fields_of(rejected(HealthAlert, {**body, "alert_id": "ALERT-0001"})) == {"body.window_end"}


@pytest.mark.parametrize(
    ("model", "body", "field"),
    [
        (HealthReadingInput, reading_body(spo2_percent=101), "body.spo2_percent"),
        (HealthReadingInput, reading_body(spo2_percent=-1), "body.spo2_percent"),
        (HealthReadingInput, reading_body(heart_rate_bpm=0), "body.heart_rate_bpm"),
        (HealthReadingInput, reading_body(respiratory_rate_bpm=-2), "body.respiratory_rate_bpm"),
        (HealthReadingInput, reading_body(mission_day=0), "body.mission_day"),
        (HealthReadingInput, reading_body(measurement_context="nap"), "body.measurement_context"),
        (HealthReadingInput, reading_body(source_type="terrestrial_biomedical"), "body.source_type"),
        (HealthReadingInput, reading_body(source_id=""), "body.source_id"),
        (HealthReadingInput, reading_body(source_id="S" * 65), "body.source_id"),
        (HealthJournalInput, journal_body(sleep_hours_last_night=24.5), "body.sleep_hours_last_night"),
        (HealthJournalInput, journal_body(sleep_hours_last_night=-0.5), "body.sleep_hours_last_night"),
        (HealthJournalInput, journal_body(mood_score=0), "body.mood_score"),
        (HealthJournalInput, journal_body(mood_score=6), "body.mood_score"),
        (HealthJournalInput, journal_body(mood_score=3.5), "body.mood_score"),
        (HealthJournalInput, journal_body(notes="x" * 2001), "body.notes"),
    ],
)
def test_shape_constraints(model, body: dict, field: str) -> None:
    assert fields_of(rejected(model, body)) == {field}


def test_fixture_messages_for_spo2_and_mood() -> None:
    spo2 = api_case("invalid_spo2_shape_constraint")
    mood = api_case("invalid_mood_score")
    assert rejected(HealthReadingInput, spo2["request"]["body"]) == spo2["response"]["body"]["error"]["details"]
    assert rejected(HealthJournalInput, mood["request"]["body"]) == mood["response"]["body"]["error"]["details"]


def test_unusual_but_well_formed_values_are_not_rejected() -> None:
    """Shape checks are not clinical ranges."""
    reading = HealthReadingInput.model_validate(
        reading_body(heart_rate_bpm=250, spo2_percent=40, respiratory_rate_bpm=0.5)
    )
    journal = HealthJournalInput.model_validate(journal_body(sleep_hours_last_night=0, mood_score=1))
    assert reading.spo2_percent == 40
    assert journal.sleep_hours_last_night == 0


def test_reading_needs_at_least_one_vital() -> None:
    case = api_case("null_only_vital_reading")
    assert rejected(HealthReadingInput, case["request"]["body"]) == case["response"]["body"]["error"]["details"]
    partial = HealthReadingInput.model_validate(
        reading_body(heart_rate_bpm=None, spo2_percent=None)
    )
    assert partial.heart_rate_bpm is None and partial.respiratory_rate_bpm == 17


@pytest.mark.parametrize("notes", [None, "", "   \n\t "])
def test_journal_needs_sleep_mood_or_a_nonblank_note(notes) -> None:
    body = journal_body(sleep_hours_last_night=None, mood_score=None, notes=notes)
    assert fields_of(rejected(HealthJournalInput, body)) == {"body"}


def test_journal_notes_are_trimmed_and_sleep_zero_counts() -> None:
    noted = HealthJournalInput.model_validate(
        journal_body(sleep_hours_last_night=None, mood_score=None, notes="  slept badly \n")
    )
    assert noted.notes == "slept badly"
    assert HealthJournalInput.model_validate(journal_body(notes=" " + "x" * 2000 + " ")).notes == "x" * 2000

    zero = HealthJournalInput.model_validate(
        journal_body(sleep_hours_last_night=0, mood_score=None, notes="  ")
    )
    assert zero.sleep_hours_last_night == 0 and zero.notes is None


def test_astronaut_rules() -> None:
    base = ASTRONAUT.model_dump()
    for changes, field in (
        ({"is_fictional": False}, "body.is_fictional"),
        ({"planned_duration_days": 0}, "body.planned_duration_days"),
        ({"mission_start_date": "2026-11-01T00:00:00Z"}, "body.mission_start_date"),
        ({"mission_start_date": "2026-02-30"}, "body.mission_start_date"),
        ({"astronaut_id": ""}, "body.astronaut_id"),
        ({"name": "  "}, "body.name"),
    ):
        assert fields_of(rejected(Astronaut, {**base, **changes})) == {field}


# --- alerts -------------------------------------------------------------------


def alert(**changes) -> dict:
    return {**alert_record(), "alert_id": "ALERT-0001", **changes}


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"unit": "%"}, "body.unit"),
        ({"indicator": "mood_score"}, "body.unit"),
        ({"indicator": "fatigue"}, "body.indicator"),
        ({"severity": "high"}, "body.severity"),
        ({"status": "acknowledged"}, "body.status"),
        ({"description": " "}, "body.description"),
        ({"explanation": ""}, "body.explanation"),
        ({"observed_value": "81"}, "body.observed_value"),
        ({"baseline_value": True}, "body.baseline_value"),
        ({"window_start": "2026-11-07T12:00:01Z"}, "body.window_end"),
        ({"window_end": "2026-11-07T12:00:01Z"}, "body.window_end"),
        ({"resolved_at": "2026-11-08T12:00:00Z"}, "body.resolved_at"),
        ({"status": "resolved"}, "body.resolved_at"),
        ({"status": "resolved", "resolved_at": "2026-11-07T11:59:59Z"}, "body.resolved_at"),
        ({"source_type": "real"}, "body.source_type"),
    ],
)
def test_alert_rules(changes: dict, field: str) -> None:
    assert fields_of(rejected(HealthAlert, alert(**changes))) == {field}


def test_alert_valid_variants() -> None:
    resolved = HealthAlert.model_validate(
        alert(status="resolved", resolved_at="2026-11-07T12:00:00Z")
    )
    assert resolved.resolved_at == "2026-11-07T12:00:00Z"
    assert HealthAlert.model_validate(alert(baseline_value=None)).baseline_value is None
    mood = HealthAlert.model_validate(alert(indicator="mood_score", unit="score", observed_value=2))
    assert mood.unit == "score"


# --- profile-dependent day ----------------------------------------------------


def test_mission_day_follows_the_utc_date() -> None:
    assert mission_day_for("2026-11-01T00:00:00Z", "2026-11-01") == 1
    assert mission_day_for("2026-11-01T23:59:59.999Z", "2026-11-01") == 1
    assert mission_day_for("2026-11-02T00:00:00Z", "2026-11-01") == 2
    assert mission_day_issues(ASTRONAUT, "2026-11-30T12:00:00Z", 30) == []


def test_inconsistent_or_out_of_mission_day_names_the_field() -> None:
    case = api_case("inconsistent_mission_day")
    body = case["request"]["body"]
    assert (
        mission_day_issues(ASTRONAUT, body["timestamp"], body["mission_day"])
        == case["response"]["body"]["error"]["details"]
    )
    for timestamp, day in (("2026-12-01T12:00:00Z", 31), ("2026-10-31T12:00:00Z", 0)):
        issues = mission_day_issues(ASTRONAUT, timestamp, day)
        assert fields_of(issues) == {"body.mission_day"}
