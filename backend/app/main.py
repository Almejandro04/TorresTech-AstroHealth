"""AstroHealth API entry point.

Builds the FastAPI app: CORS, error envelopes, the health endpoint, and the
astronaut routes. The response shapes follow docs/api_contract.md v0.1.0.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import SCHEMA_VERSION
from app.database import connect, init_schema
from app.models.responses import ResponseMeta, meta
from app.routes import ROUTERS
from app.routes.errors import install_error_handling
from app.routes.common import preserve_openapi_example_nulls

SERVICE_NAME = "astrohealth-api"

CORS_ORIGINS_ENV = "ASTROHEALTH_CORS_ORIGINS"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create missing tables at startup. Never seeds or deletes data."""
    with closing(connect()) as conn:
        init_schema(conn)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AstroHealth API", version=SCHEMA_VERSION, lifespan=lifespan)

    # Middleware added later wraps the earlier ones, so CORS is outermost.
    install_error_handling(app)
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
            data=HealthData(status="ok", service=SERVICE_NAME), meta=meta()
        )

    for router in ROUTERS:
        app.include_router(router)

    preserve_openapi_example_nulls(app, ROUTERS)

    return app


app = create_app()
