"""Contract models (docs/api_contract.md sections 3.1-3.4).

All models are strict: unknown fields are rejected, strings are not numbers,
booleans are not integers or numbers, and NaN/infinity are invalid. A JSON
integer is accepted where the contract says "number". Every field is required
even when it accepts null.
"""

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.models.fields import (
    INDICATOR_UNITS,
    AlertStatus,
    FiniteNumber,
    Identifier,
    Indicator,
    IsoDate,
    MeasurementContext,
    MoodScore,
    NonEmptyText,
    Notes,
    Percent,
    PositiveInt,
    PositiveNumber,
    Severity,
    SleepHours,
    SyntheticSourceType,
    Unit,
    UtcTimestamp,
    parse_timestamp,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SourceManifestEntry(ContractModel):
    """A provenance source. Extra descriptive manifest fields are kept."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)

    source_id: Identifier
    source_type: SyntheticSourceType
    description: str | None = None


class Astronaut(ContractModel):
    astronaut_id: Identifier
    name: NonEmptyText
    is_fictional: bool
    mission_start_date: IsoDate
    planned_duration_days: PositiveInt

    @field_validator("is_fictional")
    @classmethod
    def _only_fictional_profiles(cls, value: bool) -> bool:
        if value is not True:
            raise PydanticCustomError(
                "not_fictional", "Must be true: this MVP stores fictional profiles only."
            )
        return value


class HealthReadingInput(ContractModel):
    timestamp: UtcTimestamp
    mission_day: PositiveInt
    heart_rate_bpm: PositiveNumber | None
    spo2_percent: Percent | None
    respiratory_rate_bpm: PositiveNumber | None
    measurement_context: MeasurementContext
    source_type: SyntheticSourceType
    source_id: Identifier

    @model_validator(mode="after")
    def _at_least_one_vital(self) -> "HealthReadingInput":
        if (
            self.heart_rate_bpm is None
            and self.spo2_percent is None
            and self.respiratory_rate_bpm is None
        ):
            raise PydanticCustomError(
                "empty_record", "Provide at least one vital measurement."
            )
        return self


class HealthReading(HealthReadingInput):
    reading_id: Identifier
    astronaut_id: Identifier


class HealthJournalInput(ContractModel):
    timestamp: UtcTimestamp
    mission_day: PositiveInt
    sleep_hours_last_night: SleepHours | None
    mood_score: MoodScore | None
    notes: Notes | None
    source_type: SyntheticSourceType
    source_id: Identifier

    @model_validator(mode="after")
    def _at_least_one_value(self) -> "HealthJournalInput":
        if (
            self.sleep_hours_last_night is None
            and self.mood_score is None
            and self.notes is None
        ):
            raise PydanticCustomError(
                "empty_record", "Provide sleep hours, a mood score, or a note."
            )
        return self


class HealthJournal(HealthJournalInput):
    journal_id: Identifier
    astronaut_id: Identifier


class HealthAlertDraft(ContractModel):
    """A HealthAlert before the backend assigns its `alert_id`."""

    astronaut_id: Identifier
    timestamp: UtcTimestamp
    mission_day: PositiveInt
    indicator: Indicator
    severity: Severity
    status: AlertStatus
    description: NonEmptyText
    explanation: NonEmptyText
    rule_id: Identifier
    rule_version: Identifier
    observed_value: FiniteNumber
    baseline_value: FiniteNumber | None
    unit: Unit
    window_start: UtcTimestamp
    window_end: UtcTimestamp
    resolved_at: UtcTimestamp | None
    source_type: SyntheticSourceType
    source_id: Identifier

    # Cross-field checks run only when the fields they compare were valid;
    # an invalid field already reports its own error.

    @field_validator("unit")
    @classmethod
    def _unit_matches_indicator(cls, value: str, info: ValidationInfo) -> str:
        indicator = info.data.get("indicator")
        if indicator is not None and INDICATOR_UNITS[indicator] != value:
            raise PydanticCustomError(
                "unit_mismatch",
                "Must be {expected} for {indicator}.",
                {"expected": INDICATOR_UNITS[indicator], "indicator": indicator},
            )
        return value

    @field_validator("window_end")
    @classmethod
    def _window_is_ordered(cls, value: str, info: ValidationInfo) -> str:
        end = parse_timestamp(value)
        start = info.data.get("window_start")
        if start is not None and parse_timestamp(start) > end:
            raise PydanticCustomError(
                "window_order", "Must not be earlier than window_start."
            )
        detected = info.data.get("timestamp")
        if detected is not None and end > parse_timestamp(detected):
            raise PydanticCustomError(
                "window_order", "Must not be later than the detection timestamp."
            )
        return value

    @field_validator("resolved_at")
    @classmethod
    def _resolution_matches_status(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        status = info.data.get("status")
        if status == "active" and value is not None:
            raise PydanticCustomError(
                "resolution_mismatch", "Must be null while the alert is active."
            )
        if status == "resolved":
            if value is None:
                raise PydanticCustomError(
                    "resolution_mismatch", "Is required when the alert is resolved."
                )
            detected = info.data.get("timestamp")
            if detected is not None and parse_timestamp(value) < parse_timestamp(detected):
                raise PydanticCustomError(
                    "resolution_mismatch",
                    "Must not be earlier than the detection timestamp.",
                )
        return value


class HealthAlert(HealthAlertDraft):
    alert_id: Identifier
