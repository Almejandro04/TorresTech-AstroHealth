"""BACKEND-03 checks: REST endpoints against the shared contract fixtures."""

import copy
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import database_path
from app.database import seed_configured_database
from app.main import CORS_ORIGINS_ENV, create_app
from app.services import views

from conftest import EXAMPLES, journal_body, reading_body

CASES = json.loads((EXAMPLES / "api_examples.json").read_text(encoding="utf-8"))["cases"]

# Fixture cases whose expected body needs calculated baselines (#14) or an
# alert evaluation (#15). Everything else in them is still compared.
ANALYSIS_CASES = {
    "summary_normal_reference_fixture",
    "summary_introduced_change_and_missing_metric",
    "summary_before_later_same_day_reading",
    "summary_profile_without_observations",
    "evaluated_no_active_alerts",
    "explainable_synthetic_alert",
}
AST = "/api/astronauts/AST-001"
ORIGIN = "http://localhost:5173"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The app over a freshly seeded temporary database."""
    monkeypatch.delenv(CORS_ORIGINS_ENV, raising=False)
    seed_configured_database(database_path())
    with TestClient(create_app()) as test_client:
        yield test_client


def send(client: TestClient, case: dict):
    request = case["request"]
    return client.request(
        request["method"],
        request["path"],
        params=request.get("query"),
        json=request.get("body"),
    )


def without_analysis(body: dict) -> dict:
    """Drop the parts that only #14/#15 can produce."""
    body = copy.deepcopy(body)
    data = body.get("data")
    if isinstance(data, dict):
        data.pop("baselines", None)
        data.pop("alert_summary", None)
    else:
        body.pop("data", None)
        body["meta"].pop("total", None)
        body["meta"].pop("evaluation_status", None)
    return body


def assert_error(response, status: int, code: str) -> dict:
    body = response.json()
    assert response.status_code == status
    assert set(body) == {"error", "meta"} and "detail" not in body
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert isinstance(body["error"]["details"], list)
    assert body["meta"] == {"schema_version": "0.1.0", "as_of": None}
    return body["error"]


# --- contract fixtures --------------------------------------------------------


def test_all_fixture_cases_are_covered() -> None:
    assert len(CASES) == 24
    assert ANALYSIS_CASES <= {case["name"] for case in CASES}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=case["name"],
            marks=[pytest.mark.xfail(strict=True, reason="#14/#15: needs baselines or alert evaluation")]
            if case["name"] in ANALYSIS_CASES
            else [],
        )
        for case in CASES
    ],
)
def test_fixture_case(client: TestClient, case: dict) -> None:
    response = send(client, case)

    assert response.status_code == case["response"]["status"]
    expected = copy.deepcopy(case["response"]["body"])
    if case["name"] == "summary_before_analysis_is_implemented":
        # Explicit discrepancy, not an xfail: the #8 brief requires null here,
        # while the shared fixture says rest. Compare every other field intact.
        for name, baseline in expected["data"]["baselines"].items():
            assert baseline["measurement_context"] == (None if name == "sleep_hours_last_night" else "rest")
            baseline["measurement_context"] = None
    assert response.json() == expected


@pytest.mark.parametrize(
    "case", [pytest.param(c, id=c["name"]) for c in CASES if c["name"] in ANALYSIS_CASES]
)
def test_analysis_fixture_case_matches_outside_analysis(client: TestClient, case: dict) -> None:
    response = send(client, case)

    assert response.status_code == case["response"]["status"]
    assert without_analysis(response.json()) == without_analysis(case["response"]["body"])


# --- readings -----------------------------------------------------------------


def test_posted_readings_are_listed_in_chronological_order(client: TestClient) -> None:
    late = client.post(f"{AST}/readings", json=reading_body(timestamp="2026-11-09T12:00:00Z", mission_day=9))
    early = client.post(f"{AST}/readings", json=reading_body(timestamp="2026-11-08T06:00:00.500Z"))
    same_time = client.post(
        f"{AST}/readings", json=reading_body(timestamp="2026-11-09T12:00:00Z", mission_day=9, measurement_context="exercise")
    )
    assert [r.status_code for r in (late, early, same_time)] == [201, 201, 201]
    assert early.json()["data"]["timestamp"] == "2026-11-08T06:00:00.5Z"
    assert same_time.json()["meta"]["as_of"] == "2026-11-09T12:00:00Z"

    listed = client.get(f"{AST}/readings", params={"from_day": 7}).json()
    assert [(r["timestamp"], r["reading_id"]) for r in listed["data"]] == [
        ("2026-11-07T12:00:00Z", "READING-0007"),
        ("2026-11-08T06:00:00.5Z", "READING-0009"),
        ("2026-11-09T12:00:00Z", "READING-0008"),
        ("2026-11-09T12:00:00Z", "READING-0010"),
    ]
    assert listed["meta"] == {
        "schema_version": "0.1.0", "as_of": "2026-11-09T12:00:00Z", "total": 4, "limit": 100, "offset": 0,
    }
    assert listed["data"][0]["respiratory_rate_bpm"] is None


def test_reading_retry_and_conflict_do_not_add_rows(client: TestClient) -> None:
    assert client.post(f"{AST}/readings", json=reading_body()).status_code == 201
    retry = client.post(f"{AST}/readings", json=reading_body(timestamp="2026-11-08T12:00:00.000Z"))
    conflict = client.post(f"{AST}/readings", json=reading_body(heart_rate_bpm=99))

    assert retry.status_code == 200 and retry.json()["data"]["reading_id"] == "READING-0008"
    assert assert_error(conflict, 409, "READING_CONFLICT")["details"] == []
    listed = client.get(f"{AST}/readings").json()
    assert listed["meta"]["total"] == 8
    assert listed["data"][-1]["heart_rate_bpm"] == 85


# --- journal ------------------------------------------------------------------


def test_journal_is_created_then_corrected_with_the_same_id(client: TestClient) -> None:
    created = client.post(f"{AST}/journal", json=journal_body())
    corrected = client.post(
        f"{AST}/journal", json=journal_body(sleep_hours_last_night=0, mood_score=None, notes="  Corrected  ")
    )

    assert created.status_code == 201 and corrected.status_code == 200
    assert created.json()["data"]["journal_id"] == corrected.json()["data"]["journal_id"] == "JOURNAL-0008"

    history = client.get(f"{AST}/journal", params={"from_day": 8, "to_day": 8}).json()
    assert history["meta"]["total"] == 1
    entry = history["data"][0]
    assert entry["sleep_hours_last_night"] == 0 and entry["sleep_hours_last_night"] is not None
    assert entry["mood_score"] is None
    assert entry["notes"] == "Corrected"

    metrics = client.get(f"{AST}/summary").json()["data"]["latest_metrics"]
    assert metrics["sleep_hours_last_night"]["value"] == 0
    assert metrics["sleep_hours_last_night"]["record_id"] == "JOURNAL-0008"
    # The corrected day has no mood, so the card keeps day 7's value and time.
    assert (metrics["mood_score"]["value"], metrics["mood_score"]["mission_day"]) == (2, 7)


# --- observation cutoff -------------------------------------------------------


def test_generated_ids_remain_stable_and_link_snapshots_without_fixture_ids(client: TestClient) -> None:
    # Allocate another record first; capture server IDs instead of choosing them.
    client.post(f"{AST}/readings", json=reading_body(timestamp="2026-11-08T06:00:00Z"))
    payload = reading_body(timestamp="2026-11-08T12:00:00.1234567Z")
    created = client.post(f"{AST}/readings", json=payload)
    assert created.status_code == 201
    stored = created.json()["data"]
    retried = client.post(f"{AST}/readings", json={**payload, "timestamp": payload["timestamp"].replace("7Z", "700Z")})
    assert retried.status_code == 200 and retried.json()["data"] == stored
    assert_error(client.post(f"{AST}/readings", json={**payload, "heart_rate_bpm": 99}), 409, "READING_CONFLICT")
    summary = client.get(f"{AST}/summary").json()["data"]
    assert summary["latest_reading"]["reading_id"] == stored["reading_id"]
    assert summary["latest_metrics"]["heart_rate_bpm"]["record_id"] == stored["reading_id"]
    assert summary["latest_metrics"]["heart_rate_bpm"]["source_id"] == stored["source_id"]

    payload = journal_body(timestamp="2026-11-08T13:00:00.123456789Z")
    created = client.post(f"{AST}/journal", json=payload)
    assert created.status_code == 201
    journal_id = created.json()["data"]["journal_id"]
    edited = client.post(f"{AST}/journal", json={**payload, "notes": "Corrected by ID-independent test"})
    assert edited.status_code == 200 and edited.json()["data"]["journal_id"] == journal_id
    summary = client.get(f"{AST}/summary").json()["data"]
    assert summary["latest_metrics"]["sleep_hours_last_night"]["record_id"] == journal_id
    assert summary["latest_journal"]["journal_id"] == journal_id


def test_submicrosecond_cutoff_never_includes_the_next_observation(client: TestClient) -> None:
    prefix = "2026-11-08T12:00:00"
    for fraction, value in ((".1234567", 81), (".12345671", 82)):
        assert client.post(f"{AST}/readings", json=reading_body(timestamp=prefix + fraction + "Z", heart_rate_bpm=value)).status_code == 201
    params = {"as_of": prefix + ".1234567000Z"}
    readings = client.get(f"{AST}/readings", params=params).json()
    summary = client.get(f"{AST}/summary", params=params).json()
    assert readings["meta"]["as_of"] == prefix + ".1234567Z"
    assert readings["data"][-1]["heart_rate_bpm"] == 81
    assert readings["meta"]["total"] == 8
    assert summary["data"]["latest_metrics"]["heart_rate_bpm"]["value"] == 81


def test_default_cutoff_is_the_latest_stored_observation(client: TestClient) -> None:
    for path in ("readings", "journal", "alerts", "summary"):
        assert client.get(f"{AST}/{path}").json()["meta"]["as_of"] == "2026-11-07T12:00:00Z"

    client.post(f"{AST}/journal", json=journal_body(timestamp="2026-11-09T08:00:00Z", mission_day=9))
    summary = client.get(f"{AST}/summary").json()
    assert summary["meta"]["as_of"] == "2026-11-09T08:00:00Z"
    assert summary["data"]["mission_day"] == 9
    assert summary["data"]["latest_reading"]["mission_day"] == 7


def test_earlier_cutoff_hides_later_records(client: TestClient) -> None:
    cutoff = {"as_of": "2026-11-03T10:00:00.000Z"}

    readings = client.get(f"{AST}/readings", params=cutoff).json()
    journal = client.get(f"{AST}/journal", params=cutoff).json()
    summary = client.get(f"{AST}/summary", params=cutoff).json()

    assert readings["meta"]["as_of"] == journal["meta"]["as_of"] == "2026-11-03T10:00:00Z"
    assert [r["mission_day"] for r in readings["data"]] == [1, 2]
    assert [j["mission_day"] for j in journal["data"]] == [1, 2, 3]
    assert readings["meta"]["total"] == 2 and journal["meta"]["total"] == 3

    data = summary["data"]
    assert data["mission_day"] == 3
    assert data["latest_reading"]["reading_id"] == "READING-0002"
    assert data["latest_journal"]["journal_id"] == "JOURNAL-0003"
    assert data["latest_metrics"]["heart_rate_bpm"]["timestamp"] == "2026-11-02T12:00:00Z"
    assert data["latest_metrics"]["sleep_hours_last_night"]["timestamp"] == "2026-11-03T08:00:00Z"

    def stamps(node) -> list[str]:
        if isinstance(node, dict):
            return [v for k, v in node.items() if k in ("timestamp", "as_of") and v] + [
                s for v in node.values() for s in stamps(v)
            ]
        return [s for item in node for s in stamps(item)] if isinstance(node, list) else []

    for body in (readings, journal, summary):
        assert max(stamps(body)) <= "2026-11-03T10:00:00Z"


def test_cutoff_before_any_observation_gives_empty_views(client: TestClient) -> None:
    cutoff = {"as_of": "2026-11-01T00:00:00Z"}

    assert client.get(f"{AST}/readings", params=cutoff).json()["data"] == []
    summary = client.get(f"{AST}/summary", params=cutoff).json()
    assert summary["meta"]["as_of"] == "2026-11-01T00:00:00Z"
    assert summary["data"]["mission_day"] == 1
    assert summary["data"]["latest_reading"] is None
    assert summary["data"]["latest_metrics"]["heart_rate_bpm"]["value"] is None


@pytest.mark.parametrize(
    "as_of",
    ["2026-10-31T23:59:59Z", "2026-12-01T00:00:00Z", "2026-11-07T12:00:00", "2026-11-07T12:00:00+00:00", "yesterday", ""],
)
@pytest.mark.parametrize("path", ["readings", "journal", "alerts", "summary"])
def test_invalid_or_out_of_mission_cutoff_is_rejected(client: TestClient, path: str, as_of: str) -> None:
    error = assert_error(client.get(f"{AST}/{path}", params={"as_of": as_of}), 422, "VALIDATION_ERROR")
    assert [detail["field"] for detail in error["details"]] == ["query.as_of"]


# --- pagination and day filters -----------------------------------------------


def test_pagination_counts_after_filters(client: TestClient) -> None:
    page = client.get(f"{AST}/readings", params={"from_day": 2, "to_day": 6, "limit": 2, "offset": 3}).json()

    assert [r["mission_day"] for r in page["data"]] == [5, 6]
    assert page["meta"]["total"] == 5 and page["meta"]["limit"] == 2 and page["meta"]["offset"] == 3
    beyond = client.get(f"{AST}/journal", params={"offset": 50}).json()
    assert beyond["data"] == [] and beyond["meta"]["total"] == 7

    profiles = client.get("/api/astronauts", params={"limit": 1, "offset": 1}).json()
    assert [p["astronaut_id"] for p in profiles["data"]] == ["AST-002"]
    assert profiles["meta"] == {"schema_version": "0.1.0", "as_of": None, "total": 2, "limit": 1, "offset": 1}


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": 0}, "query.limit"),
        ({"limit": 1001}, "query.limit"),
        ({"limit": "many"}, "query.limit"),
        ({"offset": -1}, "query.offset"),
        ({"from_day": 0}, "query.from_day"),
        ({"to_day": 31}, "query.to_day"),
        ({"from_day": 5, "to_day": 4}, "query.to_day"),
        ({"from_day": "x"}, "query.from_day"),
    ],
)
@pytest.mark.parametrize("path", ["readings", "journal", "alerts"])
def test_invalid_query_is_rejected(client: TestClient, path: str, params: dict, field: str) -> None:
    error = assert_error(client.get(f"{AST}/{path}", params=params), 422, "VALIDATION_ERROR")
    assert [detail["field"] for detail in error["details"]] == [field]


def test_single_day_range_and_mission_edges_are_accepted(client: TestClient) -> None:
    one_day = client.get(f"{AST}/readings", params={"from_day": 7, "to_day": 7}).json()
    assert [r["reading_id"] for r in one_day["data"]] == ["READING-0007"]
    assert client.get(f"{AST}/journal", params={"from_day": 1, "to_day": 30}).json()["meta"]["total"] == 7
    assert client.get(f"{AST}/readings", params={"limit": 1000}).status_code == 200


# --- summary ------------------------------------------------------------------


def test_summary_metrics_keep_their_own_observation_day(client: TestClient) -> None:
    data = client.get(f"{AST}/summary").json()["data"]
    metrics = data["latest_metrics"]

    assert data["latest_reading"]["respiratory_rate_bpm"] is None
    assert (metrics["heart_rate_bpm"]["value"], metrics["heart_rate_bpm"]["mission_day"]) == (84, 7)
    respiratory = metrics["respiratory_rate_bpm"]
    assert respiratory == {
        "value": 16, "unit": "breaths/min", "timestamp": "2026-11-06T12:00:00Z", "mission_day": 6,
        "measurement_context": "rest", "source_type": "synthetic", "source_id": "SYN-CORE-001",
        "record_id": "READING-0006",
    }
    assert metrics["sleep_hours_last_night"]["measurement_context"] is None
    assert metrics["mood_score"]["value"] == 2 and isinstance(metrics["mood_score"]["value"], int)


def test_analysis_is_reported_as_not_implemented(client: TestClient) -> None:
    data = client.get(f"{AST}/summary").json()["data"]

    assert set(data["baselines"]) == {
        "heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm", "sleep_hours_last_night",
    }
    for baseline in data["baselines"].values():
        assert (baseline["status"], baseline["value"], baseline["sample_count"]) == ("not_implemented", None, 0)
        assert baseline["reference_start"] is baseline["reference_end"] is baseline["method"] is None
        assert baseline["measurement_context"] is None
    assert data["alert_summary"] == {
        "evaluation_status": "not_implemented", "active_count": None, "highest_severity": None, "recent": [],
    }

    for params in ({}, {"status": "active"}, {"status": "resolved"}):
        alerts = client.get(f"{AST}/alerts", params=params).json()
        assert alerts["data"] == []
        assert alerts["meta"]["total"] == 0
        assert alerts["meta"]["evaluation_status"] == "not_implemented"
    assert_error(client.get(f"{AST}/alerts", params={"status": "acknowledged"}), 422, "VALIDATION_ERROR")


def test_profile_without_observations(client: TestClient) -> None:
    other = "/api/astronauts/AST-002"
    summary = client.get(f"{other}/summary").json()

    assert summary["meta"] == {"schema_version": "0.1.0", "as_of": None}
    data = summary["data"]
    assert data["mission_day"] is None and data["latest_reading"] is None and data["latest_journal"] is None
    units = {name: snapshot.pop("unit") for name, snapshot in data["latest_metrics"].items()}
    assert units == {
        "heart_rate_bpm": "beats/min", "spo2_percent": "%", "respiratory_rate_bpm": "breaths/min",
        "sleep_hours_last_night": "hours", "mood_score": "score",
    }
    assert all(set(snapshot.values()) == {None} for snapshot in data["latest_metrics"].values())

    for path in ("readings", "journal", "alerts"):
        listed = client.get(f"{other}/{path}").json()
        assert listed["data"] == [] and listed["meta"]["total"] == 0 and listed["meta"]["as_of"] is None


# --- errors -------------------------------------------------------------------


@pytest.mark.parametrize("path", ["readings", "journal", "alerts", "summary"])
def test_unknown_profile_is_404_for_every_resource(client: TestClient, path: str) -> None:
    error = assert_error(client.get(f"/api/astronauts/AST-999/{path}"), 404, "ASTRONAUT_NOT_FOUND")
    assert error["message"] == "Astronaut AST-999 was not found."


def test_writes_for_an_unknown_profile_are_404(client: TestClient) -> None:
    assert_error(client.post("/api/astronauts/AST-999/readings", json=reading_body()), 404, "ASTRONAUT_NOT_FOUND")
    assert_error(client.post("/api/astronauts/AST-999/journal", json=journal_body()), 404, "ASTRONAUT_NOT_FOUND")


def test_unknown_route_and_method_use_their_own_codes(client: TestClient) -> None:
    assert_error(client.get("/api/unknown"), 404, "NOT_FOUND")
    assert_error(client.get(f"{AST}/fatigue"), 404, "NOT_FOUND")
    assert_error(client.get("/api/astronauts/AST-001"), 404, "NOT_FOUND")
    not_allowed = client.delete(f"{AST}/readings")
    assert_error(not_allowed, 405, "METHOD_NOT_ALLOWED")
    assert_error(client.post("/api/astronauts", json={}), 405, "METHOD_NOT_ALLOWED")
    assert_error(client.post(f"{AST}/alerts", json={}), 405, "METHOD_NOT_ALLOWED")


@pytest.mark.parametrize(
    ("content", "field"),
    [
        ('{"timestamp": ', "body"),
        ("not json", "body"),
        ("[]", "body"),
        ("null", "body"),
        ("", "body"),
    ],
)
def test_malformed_body_is_a_validation_error(client: TestClient, content: str, field: str) -> None:
    response = client.post(f"{AST}/readings", content=content, headers={"Content-Type": "application/json"})
    error = assert_error(response, 422, "VALIDATION_ERROR")
    assert error["details"] and all(d["field"].split(".")[0] == field for d in error["details"])


@pytest.mark.parametrize(
    ("path", "body", "field"),
    [
        ("readings", reading_body(fatigue=3), "body.fatigue"),
        ("readings", reading_body(heart_rate_bpm=True), "body.heart_rate_bpm"),
        ("readings", reading_body(timestamp="2026-11-08T12:00:00+00:00"), "body.timestamp"),
        ("readings", reading_body(source_id="SYN-UNKNOWN"), "body.source_id"),
        ("readings", reading_body(timestamp="2026-12-01T12:00:00Z", mission_day=31), "body.mission_day"),
        ("readings", reading_body(measurement_context="nap"), "body.measurement_context"),
        ("journal", journal_body(astronaut_id="AST-001"), "body.astronaut_id"),
        ("journal", journal_body(mood_score=3.5), "body.mood_score"),
        ("journal", journal_body(sleep_hours_last_night=None, mood_score=None, notes="  "), "body"),
        ("journal", journal_body(mission_day=7), "body.mission_day"),
    ],
)
def test_invalid_bodies_name_the_field_and_store_nothing(client: TestClient, path: str, body: dict, field: str) -> None:
    error = assert_error(client.post(f"{AST}/{path}", json=body), 422, "VALIDATION_ERROR")

    assert [detail["field"] for detail in error["details"]] == [field]
    assert error["message"] == "Request validation failed."
    assert client.get(f"{AST}/{path}").json()["meta"]["total"] == 7


def test_missing_body_fields_are_all_reported(client: TestClient) -> None:
    error = assert_error(client.post(f"{AST}/journal", json={"mood_score": 3}), 422, "VALIDATION_ERROR")
    assert {detail["field"] for detail in error["details"]} == {
        "body.timestamp", "body.mission_day", "body.sleep_hours_last_night", "body.notes",
        "body.source_type", "body.source_id",
    }


def test_internal_error_has_no_stack_trace(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("secret database detail at C:/private/path")

    monkeypatch.setattr(views, "build_summary", explode)
    response = client.get(f"{AST}/summary", headers={"Origin": ORIGIN})

    error = assert_error(response, 500, "INTERNAL_ERROR")
    assert error == {"code": "INTERNAL_ERROR", "message": "Internal server error.", "details": []}
    assert "secret" not in response.text and "Traceback" not in response.text
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert client.get("/api/health").status_code == 200


# --- OpenAPI ------------------------------------------------------------------


def test_openapi_lists_every_endpoint_with_models_and_examples(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    operations = {(method.upper(), path) for path, item in paths.items() for method in item}

    assert operations == {
        ("GET", "/api/health"),
        ("GET", "/api/astronauts"),
        ("GET", "/api/astronauts/{astronaut_id}/readings"),
        ("POST", "/api/astronauts/{astronaut_id}/readings"),
        ("GET", "/api/astronauts/{astronaut_id}/journal"),
        ("POST", "/api/astronauts/{astronaut_id}/journal"),
        ("GET", "/api/astronauts/{astronaut_id}/summary"),
        ("GET", "/api/astronauts/{astronaut_id}/alerts"),
    }

    def ref(operation: dict, status: str) -> str:
        return operation["responses"][status]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[1]

    def examples(operation: dict, status: str) -> set[str]:
        return set(operation["responses"][status]["content"]["application/json"].get("examples", {}))

    readings = paths["/api/astronauts/{astronaut_id}/readings"]
    assert set(readings["post"]["responses"]) == {"200", "201", "404", "409", "422"}
    assert ref(readings["post"], "200") == ref(readings["post"], "201") == "ReadingResponse"
    assert {ref(readings["post"], s) for s in ("404", "409", "422")} == {"ErrorResponse"}
    assert examples(readings["get"], "200") == {"readings_history_with_null_metric", "known_profile_empty_readings"}
    null_example = readings["get"]["responses"]["200"]["content"]["application/json"]["examples"]["readings_history_with_null_metric"]["value"]
    assert null_example["data"][-1]["respiratory_rate_bpm"] is None
    assert examples(readings["post"], "201") == {"reading_created"}
    assert examples(readings["post"], "409") == {"conflicting_reading"}
    assert "numeric_string_is_not_a_measurement" in examples(readings["post"], "422")
    request_body = readings["post"]["requestBody"]["content"]["application/json"]
    assert request_body["schema"]["$ref"].endswith("/HealthReadingInput")
    assert "reading_created" in request_body["examples"]

    journal = paths["/api/astronauts/{astronaut_id}/journal"]
    assert set(journal["post"]["responses"]) == {"200", "201", "404", "422"}
    assert ref(journal["get"], "200") == "JournalListResponse"
    assert ref(journal["post"], "200") == ref(journal["post"], "201") == "JournalResponse"

    summary = paths["/api/astronauts/{astronaut_id}/summary"]["get"]
    assert ref(summary, "200") == "SummaryResponse"
    assert examples(summary, "200") == {"summary_before_analysis_is_implemented"}

    alerts = paths["/api/astronauts/{astronaut_id}/alerts"]["get"]
    assert ref(alerts, "200") == "AlertListResponse"
    assert examples(alerts, "200") == {"alerts_not_implemented_is_not_an_all_clear"}
    assert {p["name"] for p in alerts["parameters"]} == {
        "astronaut_id", "limit", "offset", "from_day", "to_day", "as_of", "status",
    }
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    assert client.get("/docs").status_code == 200


# --- CORS and persistence -----------------------------------------------------


def test_openapi_pending_summary_example_matches_the_implemented_response(client: TestClient) -> None:
    case = next(c for c in CASES if c["name"] == "summary_before_analysis_is_implemented")
    spec = client.get("/openapi.json").json()
    example = spec["paths"]["/api/astronauts/{astronaut_id}/summary"]["get"]["responses"]["200"]["content"]["application/json"]["examples"][case["name"]]["value"]
    assert send(client, case).json() == example
    # Shared inputs are not mutated to make the example or test pass.
    assert case["response"]["body"]["data"]["baselines"]["heart_rate_bpm"]["measurement_context"] == "rest"


def test_frontend_origin_can_read_and_write(client: TestClient) -> None:
    read = client.get(f"{AST}/summary", headers={"Origin": ORIGIN})
    assert read.status_code == 200 and read.headers["access-control-allow-origin"] == ORIGIN

    preflight = client.options(
        f"{AST}/journal",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "content-type" in preflight.headers["access-control-allow-headers"].lower()

    write = client.post(
        f"{AST}/journal", json=journal_body(), headers={"Origin": ORIGIN, "Content-Type": "application/json"}
    )
    assert write.status_code == 201 and write.headers["access-control-allow-origin"] == ORIGIN

    rejected = client.post(f"{AST}/journal", json={}, headers={"Origin": ORIGIN})
    assert rejected.status_code == 422 and rejected.headers["access-control-allow-origin"] == ORIGIN

    other = client.get(f"{AST}/summary", headers={"Origin": "http://localhost:5175"})
    assert "access-control-allow-origin" not in other.headers


def test_review_ports_can_be_added_by_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_configured_database(database_path())
    monkeypatch.setenv(CORS_ORIGINS_ENV, "http://localhost:5173,http://localhost:5175,http://localhost:5176")
    with TestClient(create_app()) as configured:
        for port in (5173, 5175, 5176):
            origin = f"http://localhost:{port}"
            response = configured.get("/api/astronauts", headers={"Origin": origin})
            assert response.headers["access-control-allow-origin"] == origin


def test_data_survives_recreating_the_app(client: TestClient) -> None:
    client.post(f"{AST}/readings", json=reading_body())
    client.post(f"{AST}/journal", json=journal_body(notes="Kept"))
    client.close()

    with TestClient(create_app()) as restarted:
        readings = restarted.get(f"{AST}/readings").json()
        journal = restarted.get(f"{AST}/journal").json()
        assert readings["meta"]["total"] == journal["meta"]["total"] == 8
        assert readings["data"][-1]["reading_id"] == "READING-0008"
        assert journal["data"][-1]["notes"] == "Kept"


def test_startup_creates_the_schema_without_seeding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "fresh" / "empty.db"
    monkeypatch.setenv("ASTROHEALTH_DB_PATH", str(target))

    with TestClient(create_app()) as fresh:
        assert target.exists()
        profiles = fresh.get("/api/astronauts").json()
        assert profiles["data"] == [] and profiles["meta"]["total"] == 0
        assert_error(fresh.get("/api/astronauts/AST-001/summary"), 404, "ASTRONAUT_NOT_FOUND")
