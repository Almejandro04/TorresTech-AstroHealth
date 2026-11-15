"""AstroHealth API entry point (BACKEND-01).

Only service initialization and the health endpoint live here. The response
shapes follow docs/api_contract.md v0.1.0.
"""

import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import SCHEMA_VERSION, SchemaVersion

SERVICE_NAME = "astrohealth-api"

CORS_ORIGINS_ENV = "ASTROHEALTH_CORS_ORIGINS"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"


class ResponseMeta(BaseModel):
    """Metadata present in every response envelope."""

    schema_version: SchemaVersion
    as_of: str | None


class HealthData(BaseModel):
    status: Literal["ok"]
    service: Literal["astrohealth-api"]


class HealthResponse(BaseModel):
    data: HealthData
    meta: ResponseMeta


def parse_cors_origins(raw: str) -> list[str]:
    """Split a comma-separated list of exact origins.

    The wildcard is rejected so that allowed origins are always explicit.
    """
    origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if "*" in origins:
        raise ValueError(
            f"{CORS_ORIGINS_ENV} must list explicit origins; '*' is not supported."
        )
    return origins


def cors_origins_from_env() -> list[str]:
    """Read allowed origins; an unset or blank variable uses the local default."""
    raw = os.environ.get(CORS_ORIGINS_ENV, "")
    return parse_cors_origins(raw if raw.strip() else DEFAULT_CORS_ORIGINS)


def create_app() -> FastAPI:
    app = FastAPI(title="AstroHealth API", version=SCHEMA_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_from_env(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def get_health() -> HealthResponse:
        """Report that the API process is running."""
        return HealthResponse(
            data=HealthData(status="ok", service=SERVICE_NAME),
            meta=ResponseMeta(schema_version=SCHEMA_VERSION, as_of=None),
        )

    return app


app = create_app()
