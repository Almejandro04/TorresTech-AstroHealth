"""Vital readings of one astronaut."""

from typing import Annotated

from fastapi import APIRouter, Body, Response

from app.config import SCHEMA_VERSION
from app.database import repository
from app.models.responses import ListMeta, ReadingListResponse, ReadingResponse, meta
from app.models.schemas import HealthReadingInput
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
from app.routes.errors import ReadingConflictError
from app.services import views

router = APIRouter(prefix="/api/astronauts/{astronaut_id}/readings", tags=["readings"])

_INVALID = (
    "invalid_spo2_shape_constraint",
    "inconsistent_mission_day",
    "null_only_vital_reading",
    "numeric_string_is_not_a_measurement",
)


@router.get(
    "",
    response_model=ReadingListResponse,
    responses=documented(("readings_history_with_null_metric", "known_profile_empty_readings")),
)
def list_readings(
    astronaut_id: AstronautId,
    limit: Limit = 100,
    offset: Offset = 0,
    from_day: FromDay = None,
    to_day: ToDay = None,
    as_of: AsOf = None,
) -> ReadingListResponse:
    """Readings by (timestamp, ID) ascending. Missing metrics stay null."""
    with database() as conn:
        astronaut = repository.require_astronaut(conn, astronaut_id)
        views.check_day_range(astronaut, from_day, to_day)
        cutoff = views.resolve_as_of(conn, astronaut, as_of)
        readings = views.visible(
            repository.list_readings(conn, astronaut_id), cutoff, from_day, to_day
        )
    return ReadingListResponse(
        data=views.page(readings, limit, offset),
        meta=ListMeta(
            schema_version=SCHEMA_VERSION,
            as_of=cutoff,
            total=len(readings),
            limit=limit,
            offset=offset,
        ),
    )


@router.post(
    "",
    response_model=ReadingResponse,
    responses=documented(
        ("exact_reading_retry",),
        created=("reading_created",),
        created_model=ReadingResponse,
        conflict=("conflicting_reading",),
        invalid=_INVALID,
    ),
)
def create_reading(
    astronaut_id: AstronautId,
    payload: Annotated[
        HealthReadingInput,
        Body(openapi_examples=request_examples("reading_created", "invalid_spo2_shape_constraint")),
    ],
    response: Response,
) -> ReadingResponse:
    """Store a reading: 201 when new, 200 for an identical retry, 409 on conflict."""
    with database() as conn:
        result = repository.create_reading(conn, astronaut_id, payload)
        if result.status == "conflict":
            raise ReadingConflictError
        astronaut = repository.require_astronaut(conn, astronaut_id)
        cutoff = views.resolve_as_of(conn, astronaut, None)
    if result.status == "created":
        response.status_code = 201
    return ReadingResponse(data=result.record, meta=meta(cutoff))
