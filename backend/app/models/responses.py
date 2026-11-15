"""Response envelopes and summary models (docs/api_contract.md 3.5 and 4)."""

from typing import Literal

from pydantic import BaseModel

from app.config import SCHEMA_VERSION, SchemaVersion
from app.models.fields import MeasurementContext, Severity, SyntheticSourceType, Unit
from app.models.schemas import Astronaut, HealthAlert, HealthJournal, HealthReading

EvaluationStatus = Literal["available", "insufficient_data", "not_implemented"]


class ResponseMeta(BaseModel):
    """Metadata present in every response envelope."""

    schema_version: SchemaVersion
    as_of: str | None


class ListMeta(ResponseMeta):
    total: int
    limit: int
    offset: int


class AlertListMeta(ListMeta):
    evaluation_status: EvaluationStatus


def meta(as_of: str | None = None) -> ResponseMeta:
    return ResponseMeta(schema_version=SCHEMA_VERSION, as_of=as_of)


# --- summary ------------------------------------------------------------------


class MetricSnapshot(BaseModel):
    """Latest non-null value of one indicator, with its own observation data."""

    value: int | float | None
    unit: Unit
    timestamp: str | None
    mission_day: int | None
    measurement_context: MeasurementContext | None
    source_type: SyntheticSourceType | None
    source_id: str | None
    record_id: str | None


class LatestMetrics(BaseModel):
    heart_rate_bpm: MetricSnapshot
    spo2_percent: MetricSnapshot
    respiratory_rate_bpm: MetricSnapshot
    sleep_hours_last_night: MetricSnapshot
    mood_score: MetricSnapshot


class BaselineMetric(BaseModel):
    status: EvaluationStatus
    value: float | None
    sample_count: int
    reference_start: str | None
    reference_end: str | None
    measurement_context: MeasurementContext | None
    method: str | None


class Baselines(BaseModel):
    heart_rate_bpm: BaselineMetric
    spo2_percent: BaselineMetric
    respiratory_rate_bpm: BaselineMetric
    sleep_hours_last_night: BaselineMetric


class AlertSummary(BaseModel):
    evaluation_status: EvaluationStatus
    active_count: int | None
    highest_severity: Severity | None
    recent: list[HealthAlert]


class HealthSummary(BaseModel):
    astronaut: Astronaut
    mission_day: int | None
    latest_reading: HealthReading | None
    latest_journal: HealthJournal | None
    latest_metrics: LatestMetrics
    baselines: Baselines
    alert_summary: AlertSummary


# --- envelopes ----------------------------------------------------------------


class AstronautListResponse(BaseModel):
    data: list[Astronaut]
    meta: ListMeta


class ReadingListResponse(BaseModel):
    data: list[HealthReading]
    meta: ListMeta


class ReadingResponse(BaseModel):
    data: HealthReading
    meta: ResponseMeta


class JournalListResponse(BaseModel):
    data: list[HealthJournal]
    meta: ListMeta


class JournalResponse(BaseModel):
    data: HealthJournal
    meta: ResponseMeta


class SummaryResponse(BaseModel):
    data: HealthSummary
    meta: ResponseMeta


class AlertListResponse(BaseModel):
    data: list[HealthAlert]
    meta: AlertListMeta


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    error: ErrorBody
    meta: ResponseMeta
