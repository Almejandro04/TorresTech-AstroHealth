"""Field types shared by the contract models (docs/api_contract.md section 2).

The limits here are data-shape checks, not medical normal ranges: an unusual
but structurally valid observation is accepted.
"""

import math
import re
from datetime import date, datetime, timezone
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import AfterValidator, StringConstraints
from pydantic_core import PydanticCustomError

_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d+))?Z", re.ASCII
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


@dataclass(frozen=True, order=True)
class ExactTimestamp:
    """UTC whole second plus an exact decimal fraction, without trailing zeros.

    Fractions compare lexically: a proper prefix is the smaller fraction.
    No float, Decimal context, integer conversion, or datetime microseconds
    can round or limit the fractional digits.
    """

    second: datetime
    fraction: str

    def date(self) -> date:
        return self.second.date()


def parse_timestamp(value: str) -> ExactTimestamp:
    """Parse a contract timestamp: UTC, ending in Z, seconds required.

    All fractional digits are preserved. Offsets and zone-free values raise
    ValueError.
    """
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValueError("not a UTC timestamp ending in Z")
    moment = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    return ExactTimestamp(moment.replace(tzinfo=timezone.utc), (match.group(1) or "").rstrip("0"))


def _date_time_text(moment: datetime) -> str:
    return f"{moment.year:04d}-{moment:%m-%dT%H:%M:%S}"


def canonical_timestamp(value: str) -> str:
    """Canonical wire form: no fraction when it is zero, else trimmed zeros.

    `12:00:00Z`, `12:00:00.0Z`, and `12:00:00.000Z` all become `12:00:00Z`.
    """
    moment = parse_timestamp(value)
    fraction = f".{moment.fraction}" if moment.fraction else ""
    return f"{_date_time_text(moment.second)}{fraction}Z"


def storage_timestamp(value: str) -> str:
    """Exact storage form; SQL ordering uses ASTROHEALTH_TIMESTAMP collation.

    Keep at least six digits for existing microsecond representations, but
    never truncate longer fractions. Binary text order is NOT time order.
    """
    moment = parse_timestamp(value)
    return f"{_date_time_text(moment.second)}.{moment.fraction.ljust(6, '0')}Z"


def compare_timestamps(left: str, right: str) -> int:
    """SQLite comparison shared by ordering, uniqueness, and future cutoffs."""
    a, b = parse_timestamp(left), parse_timestamp(right)
    return (a > b) - (a < b)


def mission_day_for(timestamp: str, mission_start_date: str) -> int:
    """Day 1 is `mission_start_date`; days are UTC calendar dates."""
    observed = parse_timestamp(timestamp).date()
    return (observed - date.fromisoformat(mission_start_date)).days + 1


def _utc_timestamp(value: str) -> str:
    try:
        return canonical_timestamp(value)
    except ValueError:
        raise PydanticCustomError(
            "utc_timestamp",
            "Must be a UTC timestamp ending in Z, such as 2026-11-07T12:00:00Z.",
        ) from None


def _iso_date(value: str) -> str:
    try:
        if _DATE_RE.fullmatch(value) is None:
            raise ValueError
        date.fromisoformat(value)
    except ValueError:
        raise PydanticCustomError(
            "iso_date", "Must be an ISO calendar date, such as 2026-11-01."
        ) from None
    return value


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise PydanticCustomError("finite_number", "Must be a finite number.")
    return value


def _greater_than_zero(value: float) -> float:
    if value <= 0:
        raise PydanticCustomError("out_of_range", "Must be greater than 0.")
    return value


def _percent(value: float) -> float:
    if not 0 <= value <= 100:
        raise PydanticCustomError("out_of_range", "Must be between 0 and 100.")
    return value


def _sleep_hours(value: float) -> float:
    if not 0 <= value <= 24:
        raise PydanticCustomError("out_of_range", "Must be between 0 and 24.")
    return value


def _mood_score(value: int) -> int:
    if not 1 <= value <= 5:
        raise PydanticCustomError("out_of_range", "Must be an integer from 1 to 5.")
    return value


def _positive_int(value: int) -> int:
    if value < 1:
        raise PydanticCustomError("out_of_range", "Must be a positive integer.")
    return value


def _notes(value: str) -> str | None:
    """Trim the note; a blank note is stored as no note."""
    trimmed = value.strip()
    if len(trimmed) > 2000:
        raise PydanticCustomError(
            "too_long", "Must be at most 2,000 characters after trimming."
        )
    return trimmed or None


def _not_blank(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("blank_text", "Must not be empty.")
    return value


Identifier = Annotated[str, StringConstraints(min_length=1, max_length=64)]
NonEmptyText = Annotated[str, AfterValidator(_not_blank)]
UtcTimestamp = Annotated[str, AfterValidator(_utc_timestamp)]
IsoDate = Annotated[str, AfterValidator(_iso_date)]

FiniteNumber = Annotated[float, AfterValidator(_finite)]
PositiveNumber = Annotated[float, AfterValidator(_finite), AfterValidator(_greater_than_zero)]
Percent = Annotated[float, AfterValidator(_finite), AfterValidator(_percent)]
SleepHours = Annotated[float, AfterValidator(_finite), AfterValidator(_sleep_hours)]
MoodScore = Annotated[int, AfterValidator(_mood_score)]
PositiveInt = Annotated[int, AfterValidator(_positive_int)]
Notes = Annotated[str, AfterValidator(_notes)]

MeasurementContext = Literal["rest", "exercise", "sleep", "unknown"]
SyntheticSourceType = Literal["synthetic"]
Indicator = Literal[
    "heart_rate_bpm",
    "spo2_percent",
    "respiratory_rate_bpm",
    "sleep_hours_last_night",
    "mood_score",
]
Unit = Literal["beats/min", "%", "breaths/min", "hours", "score"]
Severity = Literal["info", "warning", "critical"]
AlertStatus = Literal["active", "resolved"]

INDICATOR_UNITS: dict[str, str] = {
    "heart_rate_bpm": "beats/min",
    "spo2_percent": "%",
    "respiratory_rate_bpm": "breaths/min",
    "sleep_hours_last_night": "hours",
    "mood_score": "score",
}
