"""BACKEND-07 regressions: future-data leakage, missing data in the rule,
the exact explanation text, and test isolation."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_DB_PATH, database_path
from app.database import seed_configured_database
from app.main import CORS_ORIGINS_ENV, create_app

from conftest import reading_body

AST = "/api/astronauts/AST-001"
OTHER = "/api/astronauts/AST-002"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv(CORS_ORIGINS_ENV, raising=False)
    seed_configured_database(database_path())
    with TestClient(create_app()) as test_client:
        yield test_client


def post(client: TestClient, profile: str, day: int, rate: float | None, time: str = "12:00:00") -> None:
    body = reading_body(timestamp=f"2026-11-{day:02d}T{time}Z", mission_day=day, heart_rate_bpm=rate)
    assert client.post(f"{profile}/readings", json=body).status_code == 201


def view(client: TestClient, as_of: str) -> tuple[dict, dict]:
    summary = client.get(f"{AST}/summary", params={"as_of": as_of}).json()
    alerts = client.get(f"{AST}/alerts", params={"as_of": as_of}).json()
    return summary, alerts


def test_rule_ignores_a_reading_later_the_same_day(client: TestClient) -> None:
    """Fails if the rule used the day-7 12:00 reading for an 11:59:59 cutoff."""
    summary, alerts = view(client, "2026-11-07T11:59:59Z")
    assert alerts["meta"]["evaluation_status"] == "available"
    assert alerts["data"] == []
    assert summary["data"]["alert_summary"]["active_count"] == 0


@pytest.mark.parametrize("as_of", ["2026-11-03T12:30:00Z", "2026-11-06T23:59:59Z", "2026-11-07T23:59:59Z"])
def test_future_readings_never_change_a_past_view(client: TestClient, as_of: str) -> None:
    """Fails if baselines or alerts used observations after `as_of`."""
    before = view(client, as_of)

    post(client, AST, 7, 200, "23:59:59.5")  # elevated, after every cutoff above
    post(client, AST, 8, 60)                 # normal: would resolve the alert
    post(client, AST, 9, 150)
    post(client, AST, 10, 150)               # would start a new event

    assert view(client, as_of) == before


def test_missing_heart_rate_breaks_the_consecutive_days(client: TestClient) -> None:
    """Day 7 has no heart rate (null), so elevated days 6 and 8 are not consecutive."""
    for day in range(1, 6):
        post(client, OTHER, day, 70)  # baseline 70, threshold 75
    post(client, OTHER, 6, 80)
    post(client, OTHER, 7, None)
    post(client, OTHER, 8, 80)

    body = client.get(f"{OTHER}/alerts").json()
    assert body["meta"]["evaluation_status"] == "available"
    assert body["data"] == []

    post(client, OTHER, 9, 80)  # days 8-9 are consecutive and elevated
    alert = client.get(f"{OTHER}/alerts").json()["data"][0]
    assert (alert["mission_day"], alert["observed_value"], alert["baseline_value"]) == (9, 80, 70)
    assert alert["window_start"] == "2026-11-08T12:00:00Z"


def test_day_7_alert_explanation_is_unchanged(client: TestClient) -> None:
    """Fails if the supported rule stops producing its expected explanation."""
    alert = client.get(f"{AST}/alerts", params={"as_of": "2026-11-07T23:59:59Z"}).json()["data"][0]
    assert (alert["rule_id"], alert["rule_version"]) == ("DEMO-HR-CHANGE", "fixture-1")
    assert alert["description"] == "Introduced synthetic resting heart-rate change."
    assert alert["explanation"] == (
        "Fixture days 6-7 have a resting mean of 81 beats/min; the synthetic days 1-5 "
        "reference mean is 72. This controlled example illustrates explanation fields, "
        "not a validated medical threshold."
    )
    assert (alert["observed_value"], alert["baseline_value"]) == (81, 72)
    assert (alert["window_start"], alert["window_end"]) == ("2026-11-06T12:00:00Z", "2026-11-07T12:00:00Z")


def test_tests_never_use_the_real_database(tmp_path: Path) -> None:
    """The autouse fixture in conftest points ASTROHEALTH_DB_PATH at tmp_path."""
    assert database_path() == tmp_path / "configured.db"
    assert database_path() != DEFAULT_DB_PATH
