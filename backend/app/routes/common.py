"""Pieces shared by the route modules: database access, query types, OpenAPI."""

import json
from copy import deepcopy
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, Path, Query
from fastapi.routing import APIRoute

from app.config import BACKEND_DIR
from app.database import connect
from app.models.responses import ErrorResponse


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    """One connection per request, opened and closed in the handler's thread."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


AstronautId = Annotated[str, Path(description="Fictional astronaut profile ID.")]
Limit = Annotated[int, Query(ge=1, le=1000, description="Page size, 1 to 1000.")]
Offset = Annotated[int, Query(ge=0, description="Records to skip.")]
FromDay = Annotated[
    int | None, Query(ge=1, description="First mission day to include (inclusive).")
]
ToDay = Annotated[
    int | None, Query(ge=1, description="Last mission day to include (inclusive).")
]
AsOf = Annotated[
    str | None,
    Query(
        description="Observation cutoff: a UTC timestamp ending in Z inside the "
        "mission. Later records are excluded. Defaults to the profile's latest "
        "stored reading or journal timestamp.",
        examples=["2026-11-07T23:59:59Z"],
    ),
]

# --- OpenAPI examples taken from the shared contract fixtures ----------------

_EXAMPLES_FILE = BACKEND_DIR.parent / "docs" / "examples" / "api_examples.json"


def _load_cases() -> dict[str, dict[str, Any]]:
    """Fixture cases by name; empty when the docs folder is not shipped."""
    try:
        bundle = json.loads(_EXAMPLES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {case["name"]: case for case in bundle["cases"]}


_CASES = _load_cases()


def _seed_baseline(value: float, context: str | None, hour: str) -> dict[str, Any]:
    return {
        "status": "available",
        "value": value,
        "sample_count": 5,
        "reference_start": f"2026-11-01T{hour}:00:00Z",
        "reference_end": f"2026-11-05T{hour}:00:00Z",
        "measurement_context": context,
        "method": "experimental_fixed_window_mean_v1",
    }


# Baselines of the demo seed for AST-001 at any cutoff from mission day 6 on.
_SEED_BASELINES_DAY_7 = {
    "heart_rate_bpm": _seed_baseline(72.0, "rest", "12"),
    "spo2_percent": _seed_baseline(98.0, "rest", "12"),
    "respiratory_rate_bpm": _seed_baseline(16.0, "rest", "12"),
    "sleep_hours_last_night": _seed_baseline(7.5, None, "08"),
}


def _examples(names: tuple[str, ...], part: str) -> dict[str, dict[str, Any]]:
    found = {}
    for name in names:
        case = _CASES.get(name)
        if case is not None:
            value = deepcopy(case["response"]["body"] if part == "response" else case["request"]["body"])
            # The shared example shows the stage before baselines existed.
            # Document what the API returns now for the same request, without
            # editing the shared fixtures; a test compares it to the live API.
            if part == "response" and name == "summary_before_analysis_is_implemented":
                value["data"]["baselines"] = deepcopy(_SEED_BASELINES_DAY_7)
            found[name] = {"summary": name.replace("_", " "), "value": value}
    return found


def request_examples(*names: str) -> dict[str, dict[str, Any]] | None:
    return _examples(names, "request") or None


def _response(model: type | None, description: str, names: tuple[str, ...]) -> dict[str, Any]:
    spec: dict[str, Any] = {"description": description}
    if model is not None:
        spec["model"] = model
    examples = _examples(names, "response")
    if examples:
        spec["content"] = {"application/json": {"examples": examples}}
    return spec


def documented(
    success: tuple[str, ...] = (),
    *,
    created: tuple[str, ...] | None = None,
    created_model: type | None = None,
    conflict: tuple[str, ...] | None = None,
    not_found: bool = True,
    invalid: tuple[str, ...] = (),
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for a route, with fixture examples per status."""
    responses: dict[int | str, dict[str, Any]] = {
        200: _response(None, "Successful response.", success),
        422: _response(ErrorResponse, "`VALIDATION_ERROR`: invalid body or query.", invalid),
    }
    if created is not None:
        responses[201] = _response(created_model, "Record created.", created)
        responses[200]["description"] = "Existing record returned or updated."
    if not_found:
        responses[404] = _response(
            ErrorResponse, "`ASTRONAUT_NOT_FOUND`: unknown profile.", ("unknown_profile",)
        )
    if conflict is not None:
        responses[409] = _response(
            ErrorResponse, "`READING_CONFLICT`: the key exists with other values.", conflict
        )
    return responses


def preserve_openapi_example_nulls(app: FastAPI, routers: tuple[APIRouter, ...]) -> None:
    """Keep explicit JSON nulls inside examples, not optional OpenAPI fields.

    FastAPI's OpenAPI encoder excludes None recursively, including arbitrary
    example payloads. Reattach the original examples after schema generation;
    missing measurements must remain visible as null in Swagger.
    """
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        spec = generate()
        # FastAPI 0.163 keeps included routers lazily in app.routes. Use the
        # explicit source routers instead of depending on private internals.
        for route in (route for router in routers for route in router.routes):
            if not isinstance(route, APIRoute) or not route.include_in_schema:
                continue
            for method in route.methods or ():
                operation = spec["paths"][route.path_format].get(method.lower())
                if operation is None:
                    continue
                for status, response in route.responses.items():
                    for media_type, content in response.get("content", {}).items():
                        if "examples" in content:
                            operation["responses"][str(status)]["content"][media_type]["examples"] = deepcopy(content["examples"])
                if route.body_field is not None:
                    examples = getattr(route.body_field.field_info, "openapi_examples", None)
                    if examples:
                        operation["requestBody"]["content"]["application/json"]["examples"] = deepcopy(examples)
        return spec

    app.openapi = openapi
