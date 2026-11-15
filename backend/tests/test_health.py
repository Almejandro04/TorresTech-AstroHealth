"""BACKEND-01 checks: health contract, OpenAPI/Swagger availability, and CORS."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import CORS_ORIGINS_ENV, create_app, parse_cors_origins

REPO_ROOT = Path(__file__).resolve().parents[2]
API_EXAMPLES = REPO_ROOT / "docs" / "examples" / "api_examples.json"

DEFAULT_ORIGIN = "http://localhost:5173"
OTHER_ORIGIN = "http://evil.example"


def health_fixture() -> dict:
    cases = json.loads(API_EXAMPLES.read_text(encoding="utf-8"))["cases"]
    return next(case for case in cases if case["name"] == "health")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv(CORS_ORIGINS_ENV, raising=False)
    return TestClient(create_app())


def preflight(client: TestClient, origin: str):
    return client.options(
        "/api/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_health_matches_contract_fixture(client: TestClient) -> None:
    case = health_fixture()

    response = client.request(case["request"]["method"], case["request"]["path"])

    assert response.status_code == case["response"]["status"] == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == case["response"]["body"]
    assert response.json() == {
        "data": {"status": "ok", "service": "astrohealth-api"},
        "meta": {"schema_version": "0.1.0", "as_of": None},
    }


def test_openapi_describes_health_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    ok_response = spec["paths"]["/api/health"]["get"]["responses"]["200"]
    assert ok_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    schemas = spec["components"]["schemas"]
    assert set(schemas["HealthResponse"]["required"]) == {"data", "meta"}
    assert set(schemas["HealthData"]["required"]) == {"status", "service"}
    assert set(schemas["ResponseMeta"]["required"]) == {"schema_version", "as_of"}


def test_swagger_ui_is_served(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text


def test_default_origin_passes_cors(client: TestClient) -> None:
    simple = client.get("/api/health", headers={"Origin": DEFAULT_ORIGIN})
    assert simple.status_code == 200
    assert simple.headers["access-control-allow-origin"] == DEFAULT_ORIGIN

    pre = preflight(client, DEFAULT_ORIGIN)
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == DEFAULT_ORIGIN
    assert "GET" in pre.headers["access-control-allow-methods"]


def test_unlisted_origin_gets_no_cors_authorization(client: TestClient) -> None:
    simple = client.get("/api/health", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in simple.headers

    pre = preflight(client, OTHER_ORIGIN)
    assert pre.status_code == 400
    assert "access-control-allow-origin" not in pre.headers


def test_multiple_origins_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        CORS_ORIGINS_ENV, "http://localhost:5173, http://127.0.0.1:5173/"
    )
    configured = TestClient(create_app())

    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = configured.get("/api/health", headers={"Origin": origin})
        assert response.headers["access-control-allow-origin"] == origin

    blocked = configured.get("/api/health", headers={"Origin": OTHER_ORIGIN})
    assert "access-control-allow-origin" not in blocked.headers


def test_wildcard_origin_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_cors_origins("http://localhost:5173,*")


def test_test_client_uses_httpx2() -> None:
    import httpx2

    assert issubclass(TestClient, httpx2.Client)
