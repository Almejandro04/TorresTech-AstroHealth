"""Daily journal entries of one astronaut (one entry per mission day)."""

from typing import Annotated

from fastapi import APIRouter, Body, Response

from app.config import SCHEMA_VERSION
from app.database import repository
from app.models.responses import JournalListResponse, JournalResponse, ListMeta, meta
from app.models.schemas import HealthJournalInput
from app.routes.common import (
    AsOf,
    AstronautId,
    FromDay,
    Limit,
    Offset,
    ToDay,
    database,
    documented,
    request_examples,
)
from app.services import views

router = APIRouter(prefix="/api/astronauts/{astronaut_id}/journal", tags=["journal"])


@router.get(
    "",
    response_model=JournalListResponse,
    responses=documented(("journal_history_for_sleep_chart",)),
)
def list_journal(
    astronaut_id: AstronautId,
    limit: Limit = 100,
    offset: Offset = 0,
    from_day: FromDay = None,
    to_day: ToDay = None,
    as_of: AsOf = None,
) -> JournalListResponse:
    """Journal entries by (timestamp, ID) ascending, for the sleep history."""
    with database() as conn:
        astronaut = repository.require_astronaut(conn, astronaut_id)
        views.check_day_range(astronaut, from_day, to_day)
        cutoff = views.resolve_as_of(conn, astronaut, as_of)
        entries = views.visible(
            repository.list_journal(conn, astronaut_id), cutoff, from_day, to_day
        )
    return JournalListResponse(
        data=views.page(entries, limit, offset),
        meta=ListMeta(
            schema_version=SCHEMA_VERSION,
            as_of=cutoff,
            total=len(entries),
            limit=limit,
            offset=offset,
        ),
    )


@router.post(
    "",
    response_model=JournalResponse,
    responses=documented(
        ("journal_day_updated_same_id",),
        created=("journal_created",),
        created_model=JournalResponse,
        invalid=("invalid_mood_score",),
    ),
)
def save_journal(
    astronaut_id: AstronautId,
    payload: Annotated[
        HealthJournalInput,
        Body(openapi_examples=request_examples("journal_created", "invalid_mood_score")),
    ],
    response: Response,
) -> JournalResponse:
    """Create the day's entry (201) or replace it keeping its ID (200)."""
    with database() as conn:
        result = repository.upsert_journal(conn, astronaut_id, payload)
        astronaut = repository.require_astronaut(conn, astronaut_id)
        cutoff = views.resolve_as_of(conn, astronaut, None)
    if result.status == "created":
        response.status_code = 201
    return JournalResponse(data=result.record, meta=meta(cutoff))
