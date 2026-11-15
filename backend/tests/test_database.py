"""BACKEND-02 checks: SQLite persistence, uniqueness, upserts, and durability."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.config import DEFAULT_DB_PATH, database_path
from app.database import (
    connect,
    count_records,
    create_reading,
    get_astronaut,
    init_schema,
    list_alerts,
    list_astronauts,
    list_journal,
    list_readings,
    resolve_alert,
    save_alert,
    transaction,
    upsert_journal,
)
from app.models import (
    AlertNotFoundError,
    AstronautNotFoundError,
    HealthAlertDraft,
    HealthJournalInput,
    HealthReadingInput,
    RecordValidationError,
)

from conftest import alert_record, api_case, journal_body, reading_body


def reading(**changes) -> HealthReadingInput:
    return HealthReadingInput.model_validate(reading_body(**changes))


def journal(**changes) -> HealthJournalInput:
    return HealthJournalInput.model_validate(journal_body(**changes))


def alert(**changes) -> HealthAlertDraft:
    return HealthAlertDraft.model_validate(alert_record(**changes))


def raw_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY seq")]


def rejected_fields(call) -> set[str]:
    with pytest.raises(RecordValidationError) as caught:
        call()
    return {detail["field"] for detail in caught.value.details}


# --- configuration and schema -------------------------------------------------


def test_database_path_comes_from_the_environment(monkeypatch, tmp_path: Path) -> None:
    assert database_path() == tmp_path / "configured.db"
    monkeypatch.setenv("ASTROHEALTH_DB_PATH", "  ")
    assert database_path() == DEFAULT_DB_PATH
    assert DEFAULT_DB_PATH.name == "astrohealth.db"


def test_schema_init_is_idempotent_and_enforces_foreign_keys(conn: sqlite3.Connection) -> None:
    create_reading(conn, "AST-001", reading())
    init_schema(conn)
    init_schema(conn)
    assert count_records(conn)["readings"] == 1
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO readings (astronaut_id, timestamp, mission_day, heart_rate_bpm,"
            " measurement_context, source_type, source_id)"
            " VALUES ('AST-404', '2026-11-08T12:00:00.000000Z', 8, 70, 'rest', 'synthetic', 'SYN-CORE-001')"
        )


def test_astronaut_reads(conn: sqlite3.Connection) -> None:
    assert [a.astronaut_id for a in list_astronauts(conn)] == ["AST-001", "AST-002"]
    assert get_astronaut(conn, "AST-001").planned_duration_days == 30
    assert get_astronaut(conn, "AST-999") is None
    for call in (list_readings, list_journal, list_alerts):
        assert call(conn, "AST-002") == []
        with pytest.raises(AstronautNotFoundError):
            call(conn, "AST-999")


# --- readings -----------------------------------------------------------------


def test_reading_created_matches_fixture_and_keeps_provenance(conn: sqlite3.Connection) -> None:
    result = create_reading(conn, "AST-001", reading())

    expected = api_case("reading_created")["response"]["body"]["data"]
    assert result.status == "created"
    assert result.record.model_dump() == {**expected, "reading_id": "READING-0001"}
    assert raw_rows(conn, "readings")[0]["timestamp"] == "2026-11-08T12:00:00.000000Z"


def test_identical_retry_returns_the_existing_reading(conn: sqlite3.Connection) -> None:
    first = create_reading(conn, "AST-001", reading())
    retry = create_reading(conn, "AST-001", reading())
    other_form = create_reading(conn, "AST-001", reading(timestamp="2026-11-08T12:00:00.000Z"))

    assert (retry.status, other_form.status) == ("existing", "existing")
    assert retry.record == other_form.record == first.record
    assert count_records(conn)["readings"] == 1


def test_conflicting_reading_changes_nothing(conn: sqlite3.Connection) -> None:
    first = create_reading(conn, "AST-001", reading())
    before = raw_rows(conn, "readings")

    different_value = create_reading(conn, "AST-001", reading(heart_rate_bpm=86))
    null_instead = create_reading(conn, "AST-001", reading(respiratory_rate_bpm=None))

    assert different_value.status == null_instead.status == "conflict"
    assert different_value.record == first.record
    assert raw_rows(conn, "readings") == before


def test_same_time_in_another_context_or_profile_is_a_new_reading(conn: sqlite3.Connection) -> None:
    create_reading(conn, "AST-001", reading())
    other_context = create_reading(conn, "AST-001", reading(measurement_context="exercise"))
    other_profile = create_reading(conn, "AST-002", reading())

    assert (other_context.status, other_profile.status) == ("created", "created")
    assert [r.reading_id for r in list_readings(conn, "AST-001")] == ["READING-0001", "READING-0002"]
    assert other_profile.record.reading_id == "READING-0003"


def test_readings_are_listed_by_time_then_id(conn: sqlite3.Connection) -> None:
    create_reading(conn, "AST-001", reading(timestamp="2026-11-08T12:00:00Z"))
    create_reading(conn, "AST-001", reading(timestamp="2026-11-08T12:00:00.5Z"))
    create_reading(conn, "AST-001", reading(timestamp="2026-11-07T09:00:00Z", mission_day=7))
    create_reading(conn, "AST-001", reading(measurement_context="sleep"))

    listed = [(r.timestamp, r.reading_id) for r in list_readings(conn, "AST-001")]
    assert listed == [
        ("2026-11-07T09:00:00Z", "READING-0003"),
        ("2026-11-08T12:00:00Z", "READING-0001"),
        ("2026-11-08T12:00:00Z", "READING-0004"),
        ("2026-11-08T12:00:00.5Z", "READING-0002"),
    ]


def test_precise_timestamp_identity_order_and_sql_cutoff(conn: sqlite3.Connection) -> None:
    prefix = "2026-11-08T12:00:00"
    for fraction in [".12345671", ".1234567", "", ".00000001", ".123456"]:
        assert create_reading(conn, "AST-001", reading(timestamp=prefix + fraction + "Z")).status == "created"
    retry = create_reading(conn, "AST-001", reading(timestamp=prefix + ".1234567000Z"))
    assert retry.status == "existing"
    assert retry.record.reading_id == "READING-0002"
    assert [r.timestamp for r in list_readings(conn, "AST-001")] == [
        prefix + f + "Z" for f in ["", ".00000001", ".123456", ".1234567", ".12345671"]
    ]
    # Test the storage predicate without implementing an HTTP/replay endpoint.
    rows = conn.execute("SELECT timestamp FROM readings WHERE timestamp <= ? ORDER BY timestamp",
                        (prefix + ".1234567Z",)).fetchall()
    assert len(rows) == 4


def test_null_and_zero_stay_distinguishable(conn: sqlite3.Connection) -> None:
    create_reading(conn, "AST-001", reading(respiratory_rate_bpm=None, spo2_percent=0))
    upsert_journal(conn, "AST-001", journal(sleep_hours_last_night=0, mood_score=None))
    upsert_journal(
        conn,
        "AST-001",
        journal(timestamp="2026-11-09T08:00:00Z", mission_day=9, sleep_hours_last_night=None),
    )

    stored_reading = raw_rows(conn, "readings")[0]
    assert stored_reading["respiratory_rate_bpm"] is None
    assert stored_reading["spo2_percent"] == 0

    stored = raw_rows(conn, "journal")
    assert stored[0]["sleep_hours_last_night"] == 0 and stored[0]["mood_score"] is None
    assert stored[1]["sleep_hours_last_night"] is None and stored[1]["notes"] is None

    day8, day9 = list_journal(conn, "AST-001")
    assert day8.sleep_hours_last_night == 0 and day8.sleep_hours_last_night is not None
    assert day9.sleep_hours_last_night is None
    assert list_readings(conn, "AST-001")[0].respiratory_rate_bpm is None


# --- profile-dependent rejections ---------------------------------------------


def test_writes_for_an_unknown_astronaut_are_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(AstronautNotFoundError):
        create_reading(conn, "AST-999", reading())
    with pytest.raises(AstronautNotFoundError):
        upsert_journal(conn, "AST-999", journal())
    with pytest.raises(AstronautNotFoundError):
        save_alert(conn, alert(astronaut_id="AST-999"))
    assert count_records(conn) == {
        "sources": 1, "astronauts": 2, "readings": 0, "journal": 0, "alerts": 0,
    }


def test_inconsistent_or_out_of_mission_day_is_rejected(conn: sqlite3.Connection) -> None:
    assert rejected_fields(lambda: create_reading(conn, "AST-001", reading(mission_day=9))) == {
        "body.mission_day"
    }
    after_mission = reading(timestamp="2026-12-01T12:00:00Z", mission_day=31)
    assert rejected_fields(lambda: create_reading(conn, "AST-001", after_mission)) == {
        "body.mission_day"
    }
    assert rejected_fields(lambda: upsert_journal(conn, "AST-001", journal(mission_day=7))) == {
        "body.mission_day"
    }
    assert rejected_fields(lambda: save_alert(conn, alert(mission_day=6))) == {"alert.mission_day"}
    assert count_records(conn)["readings"] == count_records(conn)["journal"] == 0


def test_unknown_source_is_rejected(conn: sqlite3.Connection) -> None:
    assert rejected_fields(
        lambda: create_reading(conn, "AST-001", reading(source_id="SYN-UNKNOWN"))
    ) == {"body.source_id"}
    assert rejected_fields(
        lambda: upsert_journal(conn, "AST-001", journal(source_id="SYN-UNKNOWN"))
    ) == {"body.source_id"}
    assert rejected_fields(lambda: save_alert(conn, alert(source_id="SYN-UNKNOWN"))) == {
        "alert.source_id"
    }


# --- journal ------------------------------------------------------------------


def test_journal_created_then_corrected_with_the_same_id(conn: sqlite3.Connection) -> None:
    created = upsert_journal(conn, "AST-001", journal())
    expected = api_case("journal_created")["response"]["body"]["data"]
    assert created.status == "created"
    assert created.record.model_dump() == {**expected, "journal_id": "JOURNAL-0001"}

    corrected = upsert_journal(
        conn,
        "AST-001",
        journal(timestamp="2026-11-08T21:30:00Z", sleep_hours_last_night=4.5, mood_score=None, notes="Corrected"),
    )
    assert corrected.status == "updated"
    assert corrected.record.journal_id == "JOURNAL-0001"
    assert corrected.record.sleep_hours_last_night == 4.5
    assert corrected.record.mood_score is None
    assert corrected.record.notes == "Corrected"
    assert corrected.record.timestamp == "2026-11-08T21:30:00Z"
    assert list_journal(conn, "AST-001") == [corrected.record]


def test_each_day_and_profile_has_its_own_entry(conn: sqlite3.Connection) -> None:
    upsert_journal(conn, "AST-001", journal())
    next_day = upsert_journal(
        conn, "AST-001", journal(timestamp="2026-11-09T08:00:00Z", mission_day=9)
    )
    other_profile = upsert_journal(conn, "AST-002", journal())

    assert next_day.record.journal_id == "JOURNAL-0002"
    assert other_profile.record.journal_id == "JOURNAL-0003"
    assert [j.mission_day for j in list_journal(conn, "AST-001")] == [8, 9]
    # A day-8 entry cannot be relabelled as day 9: the day must match the timestamp.
    assert rejected_fields(lambda: upsert_journal(conn, "AST-001", journal(mission_day=9))) == {
        "body.mission_day"
    }


# --- alerts -------------------------------------------------------------------


def test_alert_saved_matches_fixture(conn: sqlite3.Connection) -> None:
    saved = save_alert(conn, alert())

    expected = api_case("explainable_synthetic_alert")["response"]["body"]["data"][0]
    assert saved.status == "created"
    assert saved.record.model_dump() == expected


def test_alert_is_deduplicated_by_its_event_key(conn: sqlite3.Connection) -> None:
    first = save_alert(conn, alert())
    again = save_alert(conn, alert(timestamp="2026-11-07T12:00:00.000Z", severity="critical"))

    assert again.status == "updated"
    assert again.record.alert_id == first.record.alert_id == "ALERT-0001"
    assert again.record.severity == "critical"
    assert count_records(conn)["alerts"] == 1

    for changes in (
        {"rule_version": "fixture-2"},
        {"rule_id": "DEMO-OTHER"},
        {"indicator": "spo2_percent", "unit": "%"},
        {"timestamp": "2026-11-07T13:00:00Z"},
    ):
        assert save_alert(conn, alert(**changes)).status == "created"
    assert count_records(conn)["alerts"] == 5


def test_alert_is_resolved_without_copies(conn: sqlite3.Connection) -> None:
    saved = save_alert(conn, alert()).record

    resolved = resolve_alert(conn, saved.alert_id, "2026-11-08T12:00:00Z")
    assert (resolved.status, resolved.resolved_at) == ("resolved", "2026-11-08T12:00:00Z")
    assert list_alerts(conn, "AST-001") == [resolved]

    reopened = save_alert(conn, alert())
    assert reopened.record.alert_id == saved.alert_id
    assert (reopened.record.status, reopened.record.resolved_at) == ("active", None)

    by_upsert = save_alert(conn, alert(status="resolved", resolved_at="2026-11-09T00:00:00Z"))
    assert by_upsert.record.status == "resolved"
    assert count_records(conn)["alerts"] == 1


def test_alert_resolution_errors_change_nothing(conn: sqlite3.Connection) -> None:
    saved = save_alert(conn, alert()).record

    assert rejected_fields(lambda: resolve_alert(conn, saved.alert_id, "2026-11-07T11:00:00Z")) == {
        "alert.resolved_at"
    }
    for unknown in ("ALERT-0099", "READING-0001", "ALERT-x"):
        with pytest.raises(AlertNotFoundError):
            resolve_alert(conn, unknown, "2026-11-08T12:00:00Z")
    assert list_alerts(conn, "AST-001") == [saved]


def test_alerts_are_listed_newest_first_then_by_id(conn: sqlite3.Connection) -> None:
    save_alert(conn, alert(timestamp="2026-11-07T12:00:00Z"))
    save_alert(conn, alert(timestamp="2026-11-07T13:00:00Z"))
    save_alert(conn, alert(timestamp="2026-11-07T13:00:00Z", rule_id="DEMO-OTHER"))

    assert [a.alert_id for a in list_alerts(conn, "AST-001")] == [
        "ALERT-0002",
        "ALERT-0003",
        "ALERT-0001",
    ]


# --- atomicity and durability -------------------------------------------------


def test_failed_transaction_leaves_no_partial_data(conn: sqlite3.Connection) -> None:
    with pytest.raises(RecordValidationError):
        with transaction(conn):
            create_reading(conn, "AST-001", reading())
            upsert_journal(conn, "AST-001", journal())
            create_reading(conn, "AST-001", reading(source_id="SYN-UNKNOWN"))

    assert count_records(conn)["readings"] == count_records(conn)["journal"] == 0
    assert not conn.in_transaction
    assert create_reading(conn, "AST-001", reading()).record.reading_id == "READING-0001"


def test_records_survive_closing_and_reopening(conn: sqlite3.Connection, db_path: Path) -> None:
    stored_reading = create_reading(conn, "AST-001", reading(respiratory_rate_bpm=None)).record
    stored_journal = upsert_journal(conn, "AST-001", journal()).record
    stored_alert = save_alert(conn, alert()).record
    conn.close()

    with closing(connect(db_path)) as reopened:
        init_schema(reopened)
        assert list_readings(reopened, "AST-001") == [stored_reading]
        assert list_journal(reopened, "AST-001") == [stored_journal]
        assert list_alerts(reopened, "AST-001") == [stored_alert]
        assert stored_reading.source_id == stored_alert.source_id == "SYN-CORE-001"
        next_reading = create_reading(
            reopened, "AST-001", reading(timestamp="2026-11-09T12:00:00Z", mission_day=9)
        )
        assert next_reading.record.reading_id == "READING-0002"
