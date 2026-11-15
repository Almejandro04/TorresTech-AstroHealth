"""BACKEND-05 checks: the DEMO-HR-CHANGE rule over the seed and small changes."""

import json
from collections.abc import Iterator
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.config import database_path
from app.database import connect, count_records, seed_configured_database
from app.main import CORS_ORIGINS_ENV, create_app

from conftest import EXAMPLES, reading_body

AST = "/api/astronauts/AST-001"
DAY_6 = "2026-11-06T23:59:59Z"
DAY_7 = "2026-11-07T23:59:59Z"
FIXTURE_ALERT = next(
    case for case in json.loads((EXAMPLES / "api_examples.json").read_text(encoding="utf-8"))["cases"]
    if case["name"] == "explainable_synthetic_alert"
)["response"]["body"]["data"][0]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv(CORS_ORIGINS_ENV, raising=False)
    seed_configured_database(database_path())
    with TestClient(create_app()) as test_client:
        yield test_client


def alerts(client: TestClient, as_of: str | None = None, profile: str = AST) -> dict:
    response = client.get(f"{profile}/alerts", params={"as_of": as_of} if as_of else None)
    assert response.status_code == 200
    return response.json()


def post(client: TestClient, day: int, rate: float, time: str = "12:00:00", context: str = "rest") -> None:
    body = reading_body(timestamp=f"2026-11-{day:02d}T{time}Z", mission_day=day,
                        heart_rate_bpm=rate, measurement_context=context)
    assert client.post(f"{AST}/readings", json=body).status_code == 201


def test_one_elevated_day_does_not_trigger(client: TestClient) -> None:
    # Day 6 is 78 >= 72 + 5, but it is a single day.
    body = alerts(client, DAY_6)
    assert body["meta"]["evaluation_status"] == "available"
    assert body["data"] == [] and body["meta"]["total"] == 0
    summary = client.get(f"{AST}/summary", params={"as_of": DAY_6}).json()["data"]["alert_summary"]
    assert summary == {"evaluation_status": "available", "active_count": 0, "highest_severity": None, "recent": []}


def test_two_sustained_days_trigger_the_fixture_alert(client: TestClient) -> None:
    body = alerts(client, DAY_7)
    assert body["meta"]["evaluation_status"] == "available"
    assert len(body["data"]) == 1
    alert = body["data"][0]
    # (78 + 84) / 2 = 81; baseline 72.
    assert alert == FIXTURE_ALERT
    assert alert["alert_id"] == "ALERT-0001"

    summary = client.get(f"{AST}/summary", params={"as_of": DAY_7}).json()["data"]["alert_summary"]
    assert (summary["active_count"], summary["highest_severity"], summary["recent"]) == (1, "warning", [alert])


@pytest.mark.parametrize(("profile", "as_of"), [(AST, "2026-11-05T23:59:59Z"), ("/api/astronauts/AST-002", None)])
def test_insufficient_baseline_is_never_an_all_clear(client: TestClient, profile: str, as_of: str | None) -> None:
    body = alerts(client, as_of, profile)
    assert body["meta"]["evaluation_status"] == "insufficient_data" and body["data"] == []
    summary = client.get(f"{profile}/summary", params={"as_of": as_of} if as_of else None).json()
    assert summary["data"]["alert_summary"] == {
        "evaluation_status": "insufficient_data", "active_count": None, "highest_severity": None, "recent": [],
    }


def test_other_contexts_do_not_trigger(client: TestClient) -> None:
    seed_configured_database(database_path())
    # AST-002 has no rest baseline at all; give AST-001 elevated non-rest days 8-9.
    for day in (8, 9):
        post(client, day, 160, "15:00:00", "exercise")
        post(client, day, 150, "03:00:00", "sleep")
    body = alerts(client, "2026-11-09T23:59:59Z")
    assert [a["mission_day"] for a in body["data"]] == [7]


def test_repeated_evaluation_and_restart_keep_one_alert_and_its_id(client: TestClient) -> None:
    first = alerts(client, DAY_7)
    for _ in range(3):
        assert alerts(client, DAY_7) == first
        client.get(f"{AST}/summary")
    client.close()
    with TestClient(create_app()) as restarted:
        assert restarted.get(f"{AST}/alerts", params={"as_of": DAY_7}).json() == first
    with closing(connect(database_path())) as conn:
        assert count_records(conn)["alerts"] == 1


def test_past_cutoffs_do_not_change_with_later_data(client: TestClient) -> None:
    day_6 = alerts(client, DAY_6)
    day_7 = alerts(client, DAY_7)

    post(client, 8, 70)  # below 77: resolves the alert at day 8
    post(client, 9, 90)

    assert alerts(client, DAY_6) == day_6
    assert alerts(client, DAY_7) == day_7
    assert day_7["data"][0]["status"] == "active" and day_7["data"][0]["resolved_at"] is None


def test_a_normal_day_after_detection_resolves_the_alert(client: TestClient) -> None:
    post(client, 8, 70)

    resolved = alerts(client, "2026-11-08T23:59:59Z")["data"]
    assert len(resolved) == 1
    assert (resolved[0]["status"], resolved[0]["resolved_at"]) == ("resolved", "2026-11-08T12:00:00Z")
    assert resolved[0]["alert_id"] == "ALERT-0001"

    # Before the resolving reading the same alert reads as active.
    before = alerts(client, "2026-11-08T11:00:00Z")["data"][0]
    assert (before["status"], before["resolved_at"]) == ("active", None)

    summary = client.get(f"{AST}/summary").json()["data"]["alert_summary"]
    assert (summary["active_count"], summary["recent"]) == (0, [])
    assert alerts(client)["meta"]["total"] == 1
    assert client.get(f"{AST}/alerts", params={"status": "resolved"}).json()["meta"]["total"] == 1


def test_still_elevated_day_keeps_the_alert_active(client: TestClient) -> None:
    post(client, 8, 80)
    body = alerts(client)
    assert len(body["data"]) == 1 and body["data"][0]["status"] == "active"


def test_daily_mean_is_used_when_a_day_has_several_rest_readings(client: TestClient) -> None:
    # Day 8 at 06:00 is 70 (< 77) and resolves. Day 9: 80 and 76 -> mean 78;
    # day 10: 78. Two elevated days after the resolution day give a new event.
    post(client, 8, 70, "06:00:00")
    post(client, 9, 80, "06:00:00")
    post(client, 9, 76, "18:00:00")
    post(client, 10, 78)

    body = alerts(client, "2026-11-10T23:59:59Z")
    assert [a["mission_day"] for a in body["data"]] == [10, 7]
    new = body["data"][0]
    # (80 + 76 + 78) / 3 = 78.
    assert new["observed_value"] == 78 and new["baseline_value"] == 72
    assert (new["window_start"], new["window_end"], new["timestamp"]) == (
        "2026-11-09T06:00:00Z", "2026-11-10T12:00:00Z", "2026-11-10T12:00:00Z",
    )
    assert "days 9-10" in new["explanation"]
