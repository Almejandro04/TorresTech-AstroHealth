"""BACKEND-04 checks: analysis formulas with hand-calculated expectations.

Every expected number in this file was worked out by hand; the arithmetic is
written next to it.
"""

import math

import pytest

from app.models import Astronaut, HealthJournal, HealthReading
from app.services.analysis import (
    BASELINE_CONTEXTS,
    BASELINE_METHOD,
    IncompatibleUnitsError,
    Observation,
    analyze_indicator,
    analyze_series,
    describe,
    observations_from,
)

ASTRONAUT = Astronaut(
    astronaut_id="AST-001",
    name="Demo Astronaut 1",
    is_fictional=True,
    mission_start_date="2026-11-01",
    planned_duration_days=30,
)
DAY_6_START = "2026-11-06T00:00:00Z"
DAY_9_END = "2026-11-09T23:59:59Z"


def stamp(day: int, time: str = "12:00:00") -> str:
    return f"2026-11-{day:02d}T{time}Z"


def obs(day: int, value: float, time: str = "12:00:00", *, record_id: str | None = None,
        context: str | None = "rest", unit: str = "beats/min") -> Observation:
    return Observation(
        record_id=record_id or f"R-{day}-{time}-{context}",
        timestamp=stamp(day, time),
        mission_day=day,
        value=value,
        context=context,
        unit=unit,
    )


def analyze(observations, as_of: str = DAY_9_END, indicator: str = "heart_rate_bpm",
            context: str | None = "rest"):
    return analyze_series(observations, ASTRONAUT, indicator, as_of, context)


# Days 1-5: 76, 78, 80, 82, 84 -> sum 400, mean 400 / 5 = 80.
WINDOW = [obs(day, 74 + 2 * day) for day in range(1, 6)]


def reading(day: int, heart_rate: float | None, *, context: str = "rest", astronaut_id: str = "AST-001",
            spo2: float | None = 97, time: str = "12:00:00", number: int = 0) -> HealthReading:
    return HealthReading(
        reading_id=f"READING-{number or day:04d}",
        astronaut_id=astronaut_id,
        timestamp=stamp(day, time),
        mission_day=day,
        heart_rate_bpm=heart_rate,
        spo2_percent=spo2,
        respiratory_rate_bpm=None,
        measurement_context=context,
        source_type="synthetic",
        source_id="SYN-CORE-001",
    )


def journal(day: int, sleep: float | None, mood: int | None = 3) -> HealthJournal:
    return HealthJournal(
        journal_id=f"JOURNAL-{day:04d}",
        astronaut_id="AST-001",
        timestamp=stamp(day, "08:00:00"),
        mission_day=day,
        sleep_hours_last_night=sleep,
        mood_score=mood,
        notes=None,
        source_type="synthetic",
        source_id="SYN-CORE-001",
    )


# --- descriptive statistics ---------------------------------------------------


def test_mean_and_population_standard_deviation() -> None:
    # 2+4+4+4+5+5+7+9 = 40, mean 40/8 = 5.
    # Squared deviations: 9+1+1+1+0+0+4+16 = 32; 32/8 = 4; sqrt(4) = 2.
    stats = describe([2, 4, 4, 4, 5, 5, 7, 9])

    assert (stats.count, stats.mean, stats.minimum, stats.maximum) == (8, 5, 2, 9)
    assert stats.population_std == 2


def test_statistics_of_no_values_are_absent_not_zero() -> None:
    stats = describe([])
    assert stats.count == 0
    assert stats.mean is stats.minimum is stats.maximum is stats.population_std is None


def test_zero_variance_gives_a_standard_deviation_of_zero() -> None:
    stats = describe([72, 72, 72, 72, 72])
    assert (stats.mean, stats.population_std) == (72, 0)
    assert describe([0.1, 0.1, 0.1]).population_std == 0


def test_single_value_and_valid_zeros() -> None:
    assert describe([7.5]) == describe([7.5]) and describe([7.5]).population_std == 0
    # 0+0+6 = 6, mean 2. Squared deviations 4+4+16 = 24; 24/3 = 8; sqrt(8).
    zeros = describe([0, 0, 6])
    assert (zeros.mean, zeros.minimum) == (2, 0)
    assert zeros.population_std == pytest.approx(math.sqrt(8), rel=1e-12)


def test_extreme_values_are_kept_and_stay_finite() -> None:
    # 70+72+74+76+300 = 592, mean 118.4. The outlier is not removed.
    stats = describe([70, 72, 74, 76, 300])
    assert stats.mean == pytest.approx(118.4, rel=1e-12) and stats.maximum == 300

    huge = describe([1.7e308, 1.7e308, -1.7e308])
    assert math.isfinite(huge.mean)
    assert huge.population_std is None or math.isfinite(huge.population_std)
    with pytest.raises(ValueError):
        describe([1.0, math.nan])
    with pytest.raises(ValueError):
        describe([math.inf])


# --- reference baseline -------------------------------------------------------


def test_reference_is_the_mean_of_days_1_to_5() -> None:
    baseline = analyze(WINDOW).baseline

    assert (baseline.status, baseline.value, baseline.reason) == ("available", 80, None)
    assert (baseline.sample_count, baseline.distinct_days) == (5, 5)
    assert (baseline.reference_start, baseline.reference_end) == (stamp(1), stamp(5))


def test_reference_waits_until_day_6() -> None:
    # The window holds everything it needs, but its last day has not ended.
    for as_of in (stamp(5), "2026-11-05T23:59:59Z", "2026-11-05T23:59:59.999999999Z"):
        baseline = analyze(WINDOW, as_of).baseline
        assert (baseline.status, baseline.value) == ("insufficient_data", None)
        assert (baseline.sample_count, baseline.reason) == (5, "reference_window_open")
        assert baseline.reference_start is baseline.reference_end is None

    assert analyze(WINDOW, DAY_6_START).baseline.value == 80


def test_partial_window_counts_only_what_is_visible() -> None:
    baseline = analyze(WINDOW, stamp(3, "12:30:00")).baseline
    assert (baseline.status, baseline.sample_count, baseline.distinct_days) == ("insufficient_data", 3, 3)
    assert analyze([], DAY_9_END).baseline.sample_count == 0
    assert analyze(WINDOW, None).baseline.reason == "reference_window_open"


def test_five_readings_on_one_day_are_not_five_days() -> None:
    crowded = [obs(2, 70 + n, f"{8 + n:02d}:00:00") for n in range(5)]
    baseline = analyze(crowded).baseline

    assert (baseline.status, baseline.value) == ("insufficient_data", None)
    assert (baseline.sample_count, baseline.distinct_days) == (5, 1)
    assert baseline.reason == "too_few_distinct_days"


def test_incomplete_window_is_not_widened_with_later_days() -> None:
    # Day 5 is missing. Days 6 and 7 exist but are outside the window.
    series = WINDOW[:4] + [obs(6, 90), obs(7, 92)]
    baseline = analyze(series).baseline

    assert (baseline.status, baseline.value) == ("insufficient_data", None)
    assert (baseline.sample_count, baseline.distinct_days) == (4, 4)
    assert baseline.reason == "too_few_observations"


def test_several_readings_per_day_all_count_once_the_days_are_covered() -> None:
    # 76+78+80+82+84 = 400, plus a second day-1 reading of 88 -> 488 / 6.
    baseline = analyze(WINDOW + [obs(1, 88, "18:00:00")]).baseline
    assert (baseline.status, baseline.sample_count, baseline.distinct_days) == ("available", 6, 5)
    assert baseline.value == pytest.approx(488 / 6, rel=1e-12)
    assert baseline.reference_end == stamp(5)


def test_later_days_do_not_change_the_reference() -> None:
    before = analyze(WINDOW, DAY_6_START).baseline
    later = WINDOW + [obs(day, 150) for day in range(6, 10)]

    assert analyze(later, DAY_9_END).baseline == before
    assert analyze(later, DAY_6_START).baseline == before


def test_extreme_value_inside_the_window_is_kept() -> None:
    # 76+78+80+82+300 = 616, mean 123.2.
    baseline = analyze(WINDOW[:4] + [obs(5, 300)]).baseline
    assert baseline.value == pytest.approx(123.2, rel=1e-12)


def test_zero_reference_is_a_valid_reference() -> None:
    zeros = [obs(day, 0, unit="%") for day in range(1, 6)] + [obs(6, 3, unit="%")]
    result = analyze(zeros, indicator="spo2_percent")

    assert (result.baseline.status, result.baseline.value) == ("available", 0)
    day_6 = result.trend[-1]
    # delta = 3 - 0 = 3; a percentage of zero does not exist.
    assert (day_6.delta, day_6.percent_change, day_6.unavailable_reason) == (3, None, "reference_is_zero")
    assert result.stats.population_std is not None and math.isfinite(result.stats.population_std)


# --- trend --------------------------------------------------------------------


def test_daily_delta_and_percent_change() -> None:
    series = WINDOW + [obs(6, 86, "08:00:00"), obs(6, 90, "20:00:00"), obs(7, 72)]
    trend = {point.mission_day: point for point in analyze(series).trend}

    # Day 6: (86 + 90) / 2 = 88; delta 88 - 80 = 8; 100 * 8 / 80 = 10.
    assert (trend[6].daily_mean, trend[6].sample_count) == (88, 2)
    assert (trend[6].delta, trend[6].percent_change, trend[6].unavailable_reason) == (8, 10, None)
    # Day 7: 72 - 80 = -8; 100 * -8 / 80 = -10.
    assert (trend[7].delta, trend[7].percent_change) == (-8, -10)
    # Day 3 is 80, exactly the reference.
    assert (trend[3].delta, trend[3].percent_change) == (0, 0)
    assert list(trend) == [1, 2, 3, 4, 5, 6, 7]


def test_trend_without_reference_gives_a_reason_not_a_zero() -> None:
    trend = analyze(WINDOW[:3], stamp(3, "23:00:00")).trend

    assert [point.daily_mean for point in trend] == [76, 78, 80]
    for point in trend:
        assert point.delta is None and point.percent_change is None
        assert point.unavailable_reason == "reference_unavailable"


def test_cutoff_inside_a_day_uses_only_what_was_observed_by_then() -> None:
    series = WINDOW + [obs(6, 86, "08:00:00"), obs(6, 90, "20:00:00")]

    morning = analyze(series, stamp(6, "12:00:00")).trend[-1]
    evening = analyze(series, stamp(6, "20:00:00")).trend[-1]
    assert (morning.daily_mean, morning.sample_count, morning.delta) == (86, 1, 6)
    assert (evening.daily_mean, evening.sample_count, evening.delta) == (88, 2, 8)


def test_future_observations_do_not_change_a_past_analysis() -> None:
    past = analyze(WINDOW + [obs(6, 86)], stamp(6, "23:59:59"))
    with_future = WINDOW + [obs(6, 86), obs(6, 200, "23:59:59.5"), obs(7, 10), obs(2, 999, "13:00:00", record_id="late-import")]
    # The late import has a day-2 timestamp, so it is inside the cutoff and counts.
    assert analyze(with_future[:-1], stamp(6, "23:59:59")) == past
    assert analyze(with_future, stamp(6, "23:59:59")) != past


# --- timestamps and duplicates ------------------------------------------------


def test_cutoff_comparison_is_exact_below_the_microsecond() -> None:
    just_after = obs(5, 84, "12:00:00.0000001")
    series = WINDOW[:4] + [just_after]

    assert analyze(series, stamp(5, "12:00:00")).baseline.sample_count == 4
    assert analyze(series, stamp(5, "12:00:00.0000001")).baseline.sample_count == 5
    assert analyze(series, stamp(5, "12:00:00.00000009")).baseline.sample_count == 4
    assert analyze(series, DAY_6_START).baseline.reference_end == "2026-11-05T12:00:00.0000001Z"


def test_a_repeated_record_counts_once() -> None:
    repeated = WINDOW + [WINDOW[0], WINDOW[0], WINDOW[4]]
    result = analyze(repeated)

    assert result.baseline == analyze(WINDOW).baseline
    assert result.stats.count == 5


def test_distinct_records_with_equal_timestamps_both_count_in_id_order() -> None:
    twin = obs(5, 90, record_id="R-5-twin")
    result = analyze(WINDOW + [twin])

    # 400 + 90 = 490 over 6 observations.
    assert result.baseline.sample_count == 6
    assert result.baseline.value == pytest.approx(490 / 6, rel=1e-12)
    assert analyze([twin] + WINDOW) == result


# --- comparability ------------------------------------------------------------


def test_contexts_and_units_cannot_be_combined() -> None:
    with pytest.raises(ValueError):
        analyze(WINDOW + [obs(3, 140, context="exercise")])
    with pytest.raises(IncompatibleUnitsError):
        analyze(WINDOW + [obs(3, 1.3, "13:00:00", unit="Hz")])
    with pytest.raises(IncompatibleUnitsError):
        analyze([obs(day, 97, unit="%") for day in range(1, 6)], indicator="heart_rate_bpm")
    with pytest.raises(ValueError):
        analyze([obs(1, math.nan)])


def test_records_are_separated_by_astronaut_indicator_and_context() -> None:
    readings = [reading(day, 70 + day) for day in range(1, 7)]  # rest: 71..75 in window
    readings += [reading(day, 150, context="exercise", time="15:00:00", number=20 + day) for day in range(1, 7)]
    readings += [reading(day, 40, astronaut_id="AST-002", number=40 + day) for day in range(1, 7)]

    rest = analyze_indicator(ASTRONAUT, readings, [], "heart_rate_bpm", stamp(6))
    exercise = analyze_indicator(ASTRONAUT, readings, [], "heart_rate_bpm", stamp(6, "15:00:00"), context="exercise")
    spo2 = analyze_indicator(ASTRONAUT, readings, [], "spo2_percent", stamp(6))

    # 71+72+73+74+75 = 365, mean 73. Exercise and the other profile are excluded.
    assert (rest.context, rest.baseline.value, rest.baseline.sample_count) == ("rest", 73, 5)
    assert (exercise.context, exercise.baseline.value) == ("exercise", 150)
    assert (spo2.unit, spo2.baseline.value) == ("%", 97)
    assert rest.stats.maximum == 76 and rest.unit == "beats/min"
    assert observations_from(readings, "AST-002", "heart_rate_bpm", "rest")[0].value == 40
    assert observations_from(readings, "AST-001", "heart_rate_bpm", "sleep") == []


def test_null_is_absent_and_zero_is_a_value() -> None:
    readings = [reading(day, None if day == 3 else 70, spo2=0) for day in range(1, 7)]

    heart = analyze_indicator(ASTRONAUT, readings, [], "heart_rate_bpm", stamp(6))
    spo2 = analyze_indicator(ASTRONAUT, readings, [], "spo2_percent", stamp(6))

    assert (heart.baseline.status, heart.baseline.sample_count) == ("insufficient_data", 4)
    assert heart.baseline.reason == "too_few_observations"
    assert [point.mission_day for point in heart.trend] == [1, 2, 4, 5, 6]
    assert (spo2.baseline.status, spo2.baseline.value, spo2.baseline.sample_count) == ("available", 0, 5)


def test_sleep_uses_the_daily_journal_and_mood_is_never_averaged() -> None:
    entries = [journal(day, hours) for day, hours in enumerate([8, 7, 6, 7.5, 6.5, 5], start=1)]
    entries[1] = journal(2, 0)  # a reported zero is a value

    sleep = analyze_indicator(ASTRONAUT, [], entries, "sleep_hours_last_night", stamp(6, "08:00:00"))

    # 8+0+6+7.5+6.5 = 28, mean 5.6. Day 6: 5 - 5.6 = -0.6.
    assert (sleep.context, sleep.unit) == (None, "hours")
    assert sleep.baseline.value == pytest.approx(5.6, rel=1e-12)
    assert sleep.trend[-1].delta == pytest.approx(-0.6, rel=1e-9)
    assert "mood_score" not in BASELINE_CONTEXTS
    with pytest.raises(ValueError):
        analyze_indicator(ASTRONAUT, [], entries, "mood_score", stamp(6))


def test_no_result_is_ever_nan_or_infinite() -> None:
    series = WINDOW + [obs(6, 1e300), obs(7, 5e-324)]
    result = analyze(series)

    numbers = [result.baseline.value, result.stats.mean, result.stats.minimum, result.stats.maximum]
    numbers += [value for p in result.trend for value in (p.daily_mean, p.delta, p.percent_change)]
    numbers.append(result.stats.population_std)
    assert all(value is None or math.isfinite(value) for value in numbers)
    assert BASELINE_METHOD == "experimental_fixed_window_mean_v1"
