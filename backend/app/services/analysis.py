"""Reference baselines, descriptive statistics, and daily trends (BACKEND-04).

Experimental demonstration statistics. They are not a clinical model, a
diagnosis, or a validated threshold. Formulas, worked examples, and the
provisional policy are documented in docs/architecture/analysis.md.

Everything here is a pure function over observations. Callers pass the
observation cutoff and it is applied before anything is calculated, so no
later record can influence a result. Nothing is cached.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.models.fields import INDICATOR_UNITS, mission_day_for, parse_timestamp
from app.models.schemas import Astronaut, HealthJournal, HealthReading

# --- provisional experimental policy (pending team review) --------------------

REFERENCE_FIRST_DAY = 1
REFERENCE_LAST_DAY = 5
MIN_OBSERVATIONS = 5
MIN_DISTINCT_DAYS = 5
BASELINE_METHOD = "experimental_fixed_window_mean_v1"

# Indicator -> the one measurement context its summary reference uses.
# Sleep comes from the daily journal, which has no measurement context.
# mood_score is ordinal: it is deliberately absent and is never averaged.
BASELINE_CONTEXTS: dict[str, str | None] = {
    "heart_rate_bpm": "rest",
    "spo2_percent": "rest",
    "respiratory_rate_bpm": "rest",
    "sleep_hours_last_night": None,
}
VITAL_INDICATORS = ("heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm")

InsufficientReason = Literal[
    "reference_window_open", "too_few_observations", "too_few_distinct_days"
]
TrendReason = Literal["reference_unavailable", "reference_is_zero"]


class IncompatibleUnitsError(ValueError):
    """Observations with different or unexpected units were mixed."""


@dataclass(frozen=True)
class Observation:
    """One non-null value of one indicator, in one context, for one astronaut."""

    record_id: str
    timestamp: str
    mission_day: int
    value: float
    context: str | None
    unit: str


@dataclass(frozen=True)
class DescriptiveStats:
    """`population_std` divides by `count` (not count - 1).

    With no values, `count` is 0 and every statistic is None.
    """

    count: int
    mean: float | None
    minimum: float | None
    maximum: float | None
    population_std: float | None


@dataclass(frozen=True)
class Baseline:
    """Reference of one series. `value` is set only when it is available."""

    status: Literal["available", "insufficient_data"]
    value: float | None
    sample_count: int
    distinct_days: int
    reference_start: str | None
    reference_end: str | None
    reason: InsufficientReason | None


@dataclass(frozen=True)
class TrendPoint:
    """Mean of one mission day compared with the reference.

    `delta` and `percent_change` are None when they cannot be calculated;
    `unavailable_reason` says why. Zero is never used as a substitute.
    """

    mission_day: int
    daily_mean: float
    sample_count: int
    delta: float | None
    percent_change: float | None
    unavailable_reason: TrendReason | None


@dataclass(frozen=True)
class IndicatorAnalysis:
    """Everything calculated for one indicator in one context at one cutoff."""

    indicator: str
    context: str | None
    unit: str
    baseline: Baseline
    stats: DescriptiveStats
    trend: list[TrendPoint]


# --- observations -------------------------------------------------------------


def observations_from(
    records: Iterable[HealthReading | HealthJournal],
    astronaut_id: str,
    indicator: str,
    context: str | None,
) -> list[Observation]:
    """Extract one comparable series from stored records.

    Keeps only this astronaut, this indicator's non-null values (a valid zero
    is kept), and, for readings, exactly this measurement context. Journal
    entries have no context, so `context` must be None for them.
    """
    if indicator not in BASELINE_CONTEXTS:
        raise ValueError(f"{indicator} has no numeric analysis (mood is ordinal).")
    series = []
    for record in records:
        value = getattr(record, indicator, None)
        if record.astronaut_id != astronaut_id or value is None:
            continue
        if getattr(record, "measurement_context", None) != context:
            continue
        record_id = getattr(record, "reading_id", None) or record.journal_id
        series.append(
            Observation(
                record_id=record_id,
                timestamp=record.timestamp,
                mission_day=record.mission_day,
                value=float(value),
                context=context,
                unit=INDICATOR_UNITS[indicator],
            )
        )
    return series


def _prepare(
    observations: Iterable[Observation], as_of: str | None, expected_unit: str | None = None
) -> list[Observation]:
    """Validate, apply the cutoff, drop repeated records, and sort by time.

    A record that appears twice (same `record_id`) counts once. Distinct
    records with equal timestamps are all kept and ordered by ID. Timestamps
    are compared exactly, including digits beyond microseconds. With no
    cutoff there are no visible observations.
    """
    if as_of is None:
        return []
    cutoff = parse_timestamp(as_of)
    unique: dict[str, Observation] = {}
    for item in observations:
        if not math.isfinite(item.value):
            raise ValueError(f"{item.record_id} has a non-finite value.")
        if parse_timestamp(item.timestamp) <= cutoff:
            unique.setdefault(item.record_id, item)
    series = sorted(unique.values(), key=lambda o: (parse_timestamp(o.timestamp), o.record_id))

    units = {item.unit for item in series}
    contexts = {item.context for item in series}
    if len(units) > 1 or (expected_unit is not None and units - {expected_unit}):
        raise IncompatibleUnitsError(f"Cannot combine units: {sorted(units)}.")
    if len(contexts) > 1:
        raise ValueError(f"Cannot combine measurement contexts: {sorted(map(str, contexts))}.")
    return series


# --- formulas -----------------------------------------------------------------


def _mean(values: Sequence[float]) -> float:
    low, high = min(values), max(values)
    if low == high:
        # Identical values: return that value exactly. Summing and dividing
        # can round (0.1 + 0.1 + 0.1) / 3 away from 0.1.
        return low
    try:
        mean = math.fsum(values) / len(values)
    except OverflowError:
        # The sum of very large finite values can overflow; their mean cannot.
        mean = math.fsum(value / len(values) for value in values)
    return min(max(mean, low), high)


def describe(values: Sequence[float]) -> DescriptiveStats:
    """Count, mean, minimum, maximum, and population standard deviation.

    mean = sum(x) / n;  population_std = sqrt(sum((x - mean)^2) / n).
    Identical values give a standard deviation of exactly 0. Outliers are
    kept. A standard deviation too large for a float is reported as None
    rather than infinity.
    """
    if not values:
        return DescriptiveStats(0, None, None, None, None)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Statistics need finite values.")
    mean = _mean(values)
    deviations = [value - mean for value in values]
    scale = max(abs(d) for d in deviations)
    if scale == 0:
        std: float | None = 0.0
    elif math.isfinite(scale):
        std = scale * math.sqrt(math.fsum((d / scale) ** 2 for d in deviations) / len(values))
        std = std if math.isfinite(std) else None
    else:
        std = None
    return DescriptiveStats(len(values), mean, min(values), max(values), std)


def reference_baseline(observations: Sequence[Observation], as_of_day: int | None) -> Baseline:
    """Fixed-window mean of an already prepared series.

    Uses only mission days 1-5. It is available when the cutoff has reached
    day 6 (the window is over) and the window holds at least 5 observations
    on at least 5 distinct days. The window is never widened with later days,
    and later observations never change the value.
    """
    window = [
        item for item in observations
        if REFERENCE_FIRST_DAY <= item.mission_day <= REFERENCE_LAST_DAY
    ]
    days = len({item.mission_day for item in window})

    reason: InsufficientReason | None = None
    if as_of_day is None or as_of_day <= REFERENCE_LAST_DAY:
        reason = "reference_window_open"
    elif len(window) < MIN_OBSERVATIONS:
        reason = "too_few_observations"
    elif days < MIN_DISTINCT_DAYS:
        reason = "too_few_distinct_days"

    if reason is not None:
        return Baseline("insufficient_data", None, len(window), days, None, None, reason)
    return Baseline(
        status="available",
        value=_mean([item.value for item in window]),
        sample_count=len(window),
        distinct_days=days,
        reference_start=window[0].timestamp,
        reference_end=window[-1].timestamp,
        reason=None,
    )


def daily_trend(observations: Sequence[Observation], baseline: Baseline) -> list[TrendPoint]:
    """One point per mission day that has observations, in day order.

    daily_mean = mean of that day's values;  delta = daily_mean - reference;
    percent_change = 100 * delta / reference, only for a non-zero reference.
    Daily means are internal aggregates: they never replace stored records.
    """
    by_day: dict[int, list[float]] = {}
    for item in observations:
        by_day.setdefault(item.mission_day, []).append(item.value)

    points = []
    for day in sorted(by_day):
        mean = _mean(by_day[day])
        delta = percent = None
        reason: TrendReason | None = None
        if baseline.value is None:
            reason = "reference_unavailable"
        else:
            delta = mean - baseline.value
            if baseline.value == 0:
                reason = "reference_is_zero"
            else:
                percent = 100 * delta / baseline.value
                if not math.isfinite(percent):
                    percent = None
        points.append(TrendPoint(day, mean, len(by_day[day]), delta, percent, reason))
    return points


# --- one series, one astronaut --------------------------------------------------


def analyze_series(
    observations: Iterable[Observation],
    astronaut: Astronaut,
    indicator: str,
    as_of: str | None,
    context: str | None = None,
) -> IndicatorAnalysis:
    """Baseline, statistics, and trend of one comparable series at `as_of`.

    Every observation must be in `context`; a mixed series is rejected.
    """
    unit = INDICATOR_UNITS[indicator]
    series = _prepare(observations, as_of, unit)
    if any(item.context != context for item in series):
        raise ValueError(f"Observations are not all in the {context!r} context.")
    as_of_day = None if as_of is None else mission_day_for(as_of, astronaut.mission_start_date)
    baseline = reference_baseline(series, as_of_day)
    return IndicatorAnalysis(
        indicator=indicator,
        context=context,
        unit=unit,
        baseline=baseline,
        stats=describe([item.value for item in series]),
        trend=daily_trend(series, baseline),
    )


def analyze_indicator(
    astronaut: Astronaut,
    readings: Iterable[HealthReading],
    journal: Iterable[HealthJournal],
    indicator: str,
    as_of: str | None,
    context: str | None = None,
) -> IndicatorAnalysis:
    """Analysis of one indicator from stored records.

    Vital indicators default to the `rest` context used by the summary; pass
    another context to analyze it on its own. Contexts are never merged.
    """
    if indicator in VITAL_INDICATORS:
        records: Iterable[HealthReading | HealthJournal] = readings
        context = context or BASELINE_CONTEXTS[indicator]
    else:
        records, context = journal, None
    series = observations_from(records, astronaut.astronaut_id, indicator, context)
    return analyze_series(series, astronaut, indicator, as_of, context)
