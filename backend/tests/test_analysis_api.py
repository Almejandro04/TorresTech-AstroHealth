"""BACKEND-04 checks: calculated baselines in the summary, alerts still pending."""

import json
import math
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import database_path
from app.database import seed_configured_database
from app.main import CORS_ORIGINS_ENV, create_app

from conftest import EXAMPLES, journal_body, reading_body

CASES = {
    case["name"]: case
    for case in json.loads((EXAMPLES / "api_examples.json").read_text(encoding="utf-8"))["cases"]
}
AST = "/api/astronauts/AST-001"
OTHER = "/api/astronauts/AST-002"
METHOD = "experimental_fixed_window_mean_v1"
VITALS = ("heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm")

# Seed, days 1-5: heart rate 72 x5, SpO2 98 x5, respiratory rate 16 x5 (rest,
# 12:00Z each day) and 7.5 h of sleep x5 (08:00Z). Each mean is the repeated value.
SEED_BASELINES = {
    name: {
        "status": "available", "value": value, "sample_count": 5,
        "reference_start": f"2026-11-01T{hour}:00:00Z", "reference_end": f"2026-11-05T{hour}:00:00Z",
        "measurement_context": context, "method": METHOD,
    }
    for name, value, context, hour in (
        ("heart_rate_bpm", 72, "rest", "12"),
        ("spo2_percent", 98, "rest", "12"),
        ("respiratory_rate_bpm", 16, "rest", "12"),
        ("sleep_hours_last_night", 7.5, None, "08"),
    )
}
PENDING_ALERTS = {"evaluation_status": "not_implemented", "active_count": None, "highest_severity": None, "recent": []}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The app over a freshly seeded temporary database."""
    monkeypatch.delenv(CORS_ORIGINS_ENV, raising=False)
    seed_configured_database(database_path())
    with TestClient(create_app()) as test_client:
        yield test_client


def summary(client: TestClient, profile: str = AST, as_of: str | None = None) -> dict:
    response = client.get(f"{profile}/summary", params={"as_of": as_of} if as_of else None)
    assert response.status_code == 200
    return response.json()


def baselines(client: TestClient, profile: str = AST, as_of: str | None = None) -> dict:
    return summary(client, profile, as_of)["data"]["baselines"]


def insufficient(count: int, context: str | None) -> dict:
    return {
        "status": "insufficient_data", "value": None, "sample_count": count,
        "reference_start": None, "reference_end": None, "measurement_context": context, "method": None,
    }


def fixture_baselines(name: str) -> dict:
    return CASES[name]["response"]["body"]["data"]["baselines"]


# --- states -------------------------------------------------------------------


def test_profile_without_data_matches_the_fixture_baselines(client: TestClient) -> None:
    body = summary(client, OTHER)

    assert body["data"]["baselines"] == fixture_baselines("summary_profile_without_observations")
    assert body["data"]["baselines"]["heart_rate_bpm"] == insufficient(0, "rest")
    assert body["data"]["baselines"]["sleep_hours_last_night"] == insufficient(0, None)
    assert body["data"]["alert_summary"] == PENDING_ALERTS


def test_early_cutoff_reports_insufficient_data_with_real_counts(client: TestClient) -> None:
    day_3 = baselines(client, as_of="2026-11-03T12:30:00Z")
    assert day_3 == {**{name: insufficient(3, "rest") for name in VITALS}, "sleep_hours_last_night": insufficient(3, None)}

    # Day 3 at 10:00: the day-3 journal (08:00) is in, the day-3 reading (12:00) is not.
    morning = baselines(client, as_of="2026-11-03T10:00:00Z")
    assert (morning["heart_rate_bpm"]["sample_count"], morning["sleep_hours_last_night"]["sample_count"]) == (2, 3)


def test_reference_becomes_available_when_day_6_starts(client: TestClient) -> None:
    end_of_day_5 = baselines(client, as_of="2026-11-05T23:59:59Z")
    assert end_of_day_5 == {**{name: insufficient(5, "rest") for name in VITALS}, "sleep_hours_last_night": insufficient(5, None)}

    assert baselines(client, as_of="2026-11-06T00:00:00Z") == SEED_BASELINES
    assert baselines(client) == SEED_BASELINES


def test_summary_has_baselines_and_alerts_are_still_pending(client: TestClient) -> None:
    body = summary(client)
    data = body["data"]

    assert data["baselines"] == SEED_BASELINES
    assert data["alert_summary"] == PENDING_ALERTS
    alerts = client.get(f"{AST}/alerts").json()
    assert alerts["data"] == [] and alerts["meta"]["evaluation_status"] == "not_implemented"
    # Baselines do not touch the per-indicator snapshots or the raw history.
    assert data["latest_metrics"]["respiratory_rate_bpm"]["mission_day"] == 6
    assert data["latest_reading"]["respiratory_rate_bpm"] is None
    assert set(data["baselines"]) == {"heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm", "sleep_hours_last_night"}
    assert "mood_score" not in data["baselines"]


# --- shared fixtures ----------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["summary_introduced_change_and_missing_metric", "summary_before_later_same_day_reading"]
)
def test_baseline_values_match_the_fixtures_from_day_6(client: TestClient, name: str) -> None:
    case = CASES[name]
    actual = baselines(client, as_of=case["request"]["query"]["as_of"])
    expected = fixture_baselines(name)

    compared = ("status", "value", "sample_count", "measurement_context")
    for indicator, baseline in expected.items():
        assert {key: actual[indicator][key] for key in compared} == {key: baseline[key] for key in compared}
    # Documented differences: the fixtures show the window's calendar bounds and
    # an illustrative method name; the API reports the observations it used.
    assert expected["heart_rate_bpm"]["method"] == "fixture_reference_mean"
    assert (expected["heart_rate_bpm"]["reference_start"], expected["heart_rate_bpm"]["reference_end"]) == (
        "2026-11-01T00:00:00Z", "2026-11-05T23:59:59Z",
    )
    assert actual == SEED_BASELINES


def test_documented_difference_at_the_last_second_of_day_5(client: TestClient) -> None:
    """The fixture calls the reference available at 23:59:59 of day 5.

    The provisional policy waits for day 6, so the API still reports
    insufficient_data there, with the same five observations counted.
    """
    case = CASES["summary_normal_reference_fixture"]
    assert case["request"]["query"]["as_of"] == "2026-11-05T23:59:59Z"
    expected = fixture_baselines("summary_normal_reference_fixture")
    actual = baselines(client, as_of="2026-11-05T23:59:59Z")

    for indicator, baseline in expected.items():
        assert (baseline["status"], baseline["sample_count"]) == ("available", 5)
        assert (actual[indicator]["status"], actual[indicator]["sample_count"]) == ("insufficient_data", 5)
        assert actual[indicator]["measurement_context"] == baseline["measurement_context"]


# --- reproducibility ----------------------------------------------------------


def test_later_data_keeps_the_reference_and_past_views(client: TestClient) -> None:
    past_cutoff = "2026-11-07T09:00:00Z"
    before_past = summary(client, as_of=past_cutoff)
    before_now = summary(client)

    for day, rate in ((8, 130), (9, 135), (10, 140)):
        posted = client.post(
            f"{AST}/readings",
            json=reading_body(timestamp=f"2026-11-{day:02d}T12:00:00Z", mission_day=day, heart_rate_bpm=rate),
        )
        assert posted.status_code == 201
    assert client.post(f"{AST}/journal", json=journal_body(sleep_hours_last_night=2)).status_code == 201

    now = summary(client)
    assert now["meta"]["as_of"] == "2026-11-10T12:00:00Z"
    assert now["data"]["baselines"] == SEED_BASELINES == before_now["data"]["baselines"]
    assert now["data"]["latest_metrics"]["heart_rate_bpm"]["value"] == 140
    assert summary(client, as_of=past_cutoff) == before_past
    assert summary(client, as_of="2026-11-07T12:00:00Z") == before_now


def test_other_contexts_do_not_enter_the_rest_reference(client: TestClient) -> None:
    for day in range(1, 6):
        posted = client.post(
            f"{AST}/readings",
            json=reading_body(
                timestamp=f"2026-11-{day:02d}T15:00:00Z", mission_day=day,
                heart_rate_bpm=150, measurement_context="exercise",
            ),
        )
        assert posted.status_code == 201

    assert baselines(client) == SEED_BASELINES


def test_missing_values_reduce_the_count_and_zero_does_not(client: TestClient) -> None:
    # AST-002: SpO2 on six days; heart rate missing on day 5; respiratory rate never.
    for day in range(1, 7):
        body = reading_body(
            timestamp=f"2026-11-{day:02d}T12:00:00Z", mission_day=day,
            heart_rate_bpm=None if day == 5 else 60 + day, spo2_percent=0 if day == 2 else 95,
            respiratory_rate_bpm=None,
        )
        assert client.post(f"{OTHER}/readings", json=body).status_code == 201

    result = baselines(client, OTHER)
    assert result["heart_rate_bpm"] == insufficient(4, "rest")
    assert result["respiratory_rate_bpm"] == insufficient(0, "rest")
    assert result["sleep_hours_last_night"] == insufficient(0, None)
    # 95+0+95+95+95 = 380, mean 76. The valid zero is part of the mean.
    assert result["spo2_percent"] == {
        "status": "available", "value": 76, "sample_count": 5,
        "reference_start": "2026-11-01T12:00:00Z", "reference_end": "2026-11-05T12:00:00Z",
        "measurement_context": "rest", "method": METHOD,
    }
    # AST-001 is unaffected by another profile's data.
    assert baselines(client) == SEED_BASELINES


def test_five_readings_on_one_day_do_not_make_a_reference(client: TestClient) -> None:
    for hour in range(8, 13):
        body = reading_body(timestamp=f"2026-11-02T{hour:02d}:00:00Z", mission_day=2)
        assert client.post(f"{OTHER}/readings", json=body).status_code == 201
    client.post(f"{OTHER}/readings", json=reading_body(timestamp="2026-11-06T12:00:00Z", mission_day=6))

    assert baselines(client, OTHER)["heart_rate_bpm"] == insufficient(5, "rest")


def test_a_journal_correction_changes_that_days_analysis(client: TestClient) -> None:
    """`as_of` is an observation cutoff, not a database history."""
    corrected = client.post(
        f"{AST}/journal",
        json=journal_body(timestamp="2026-11-03T08:00:00Z", mission_day=3, sleep_hours_last_night=2.5, mood_score=4),
    )
    assert corrected.status_code == 200

    sleep = baselines(client, as_of="2026-11-06T00:00:00Z")["sleep_hours_last_night"]
    # 7.5 * 4 + 2.5 = 32.5, mean 6.5.
    assert (sleep["status"], sleep["value"], sleep["sample_count"]) == ("available", 6.5, 5)


def test_identical_retries_do_not_add_weight(client: TestClient) -> None:
    seed = json.loads((EXAMPLES / "mission_seed.json").read_text(encoding="utf-8"))
    for record in seed["readings"][:5]:
        body = {key: value for key, value in record.items() if key != "astronaut_id"}
        body["timestamp"] = body["timestamp"].replace("Z", ".000Z")
        assert client.post(f"{AST}/readings", json=body).status_code == 200
    seed_configured_database(database_path())

    assert baselines(client) == SEED_BASELINES


# --- frontend invariants ------------------------------------------------------


@pytest.mark.parametrize(
    "as_of", [None, "2026-11-01T00:00:00Z", "2026-11-05T23:59:59Z", "2026-11-06T00:00:00Z", "2026-11-07T09:00:00Z"]
)
def test_baseline_shapes_satisfy_the_frontend_guards(client: TestClient, as_of: str | None) -> None:
    """Mirrors `baseline` and `matchesView` in frontend/src/services/responseValidation.ts."""
    body = summary(client, as_of=as_of)
    cutoff = body["meta"]["as_of"]

    for baseline in body["data"]["baselines"].values():
        assert set(baseline) == {
            "status", "value", "sample_count", "reference_start", "reference_end", "measurement_context", "method",
        }
        assert baseline["status"] in ("available", "insufficient_data")
        assert baseline["value"] is None or math.isfinite(baseline["value"])
        assert isinstance(baseline["sample_count"], int) and baseline["sample_count"] >= 0
        assert baseline["measurement_context"] in (None, "rest")
        assert baseline["method"] is None or baseline["method"]
        if baseline["status"] == "available":
            assert baseline["value"] is not None
            assert baseline["reference_start"] <= baseline["reference_end"] <= cutoff
        else:
            assert baseline["value"] is baseline["reference_start"] is baseline["reference_end"] is None
