"""Astronaut profiles and the per-astronaut dashboard summary."""

from fastapi import APIRouter

from app.config import SCHEMA_VERSION
from app.database import repository
from app.models.responses import AstronautListResponse, ListMeta, SummaryResponse, meta
from app.routes.common import AsOf, AstronautId, Limit, Offset, database, documented
from app.services import views

router = APIRouter(prefix="/api/astronauts", tags=["astronauts"])


@router.get(
    "",
    response_model=AstronautListResponse,
    responses=documented(("fictional_profiles",), not_found=False),
)
def list_astronauts(limit: Limit = 100, offset: Offset = 0) -> AstronautListResponse:
    """Fictional profiles, sorted by ID."""
    with database() as conn:
        profiles = repository.list_astronauts(conn)
    return AstronautListResponse(
        data=views.page(profiles, limit, offset),
        meta=ListMeta(
            schema_version=SCHEMA_VERSION,
            as_of=None,
            total=len(profiles),
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/{astronaut_id}/summary",
    response_model=SummaryResponse,
    tags=["summary"],
    responses=documented(
        ("summary_before_analysis_is_implemented",),
    ),
)
def get_summary(astronaut_id: AstronautId, as_of: AsOf = None) -> SummaryResponse:
    """Latest records and the latest non-null value of each indicator.

    Baselines and the alert summary report `not_implemented` until their
    issues land; that is not a statement about the astronaut's health.
    """
    with database() as conn:
        astronaut = repository.require_astronaut(conn, astronaut_id)
        cutoff = views.resolve_as_of(conn, astronaut, as_of)
        summary = views.build_summary(conn, astronaut, cutoff)
    return SummaryResponse(data=summary, meta=meta(cutoff))
