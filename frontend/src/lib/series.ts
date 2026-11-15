import type { HealthJournal, HealthReading, MeasurementContext, MetricName } from '../types/health'
import { CONTEXT_LABELS, METRICS } from './metrics'

export type SeriesKey = MeasurementContext | 'journal'

export interface SeriesPoint {
  t: number
  day: number
  timestamp: string
  value: number
  recordId: string
}

export interface MetricSeries {
  key: SeriesKey
  label: string
  points: SeriesPoint[]
}

/** A record that exists but carries no value for this metric (an explicit `null`). */
export interface EmptyRecord {
  t: number
  day: number
  timestamp: string
  seriesKey: SeriesKey
  recordId: string
}

export interface MetricHistory {
  metric: MetricName
  series: MetricSeries[]
  emptyRecords: EmptyRecord[]
  /** Elapsed days in the range with no recorded value at all. Charts keep them as gaps. */
  missingDays: number[]
  observationCount: number
}

export interface DayRange {
  fromDay: number
  toDay: number
}

const SERIES_ORDER: SeriesKey[] = ['rest', 'exercise', 'sleep', 'unknown', 'journal']

/**
 * Splits a metric's history into one series per comparable context. Readings of different
 * contexts are never joined into one line, and no value is carried forward into a gap.
 */
export function buildMetricHistory(
  metric: MetricName,
  readings: HealthReading[],
  journal: HealthJournal[],
  range: DayRange,
): MetricHistory {
  const grouped = new Map<SeriesKey, SeriesPoint[]>()
  const emptyRecords: EmptyRecord[] = []

  const add = (key: SeriesKey, value: number | null, record: { timestamp: string; mission_day: number }, recordId: string) => {
    if (record.mission_day < range.fromDay || record.mission_day > range.toDay) return
    const t = Date.parse(record.timestamp)
    if (value === null) {
      emptyRecords.push({ t, day: record.mission_day, timestamp: record.timestamp, seriesKey: key, recordId })
      return
    }
    const points = grouped.get(key) ?? []
    points.push({ t, day: record.mission_day, timestamp: record.timestamp, value, recordId })
    grouped.set(key, points)
  }

  if (METRICS[metric].source === 'reading') {
    const field = metric as 'heart_rate_bpm' | 'spo2_percent' | 'respiratory_rate_bpm'
    for (const reading of readings) add(reading.measurement_context, reading[field], reading, reading.reading_id)
  } else {
    const field = metric as 'sleep_hours_last_night' | 'mood_score'
    for (const entry of journal) add('journal', entry[field], entry, entry.journal_id)
  }

  const series = SERIES_ORDER.filter((key) => grouped.has(key)).map((key): MetricSeries => ({
    key,
    label: key === 'journal' ? 'Daily entry' : `${CONTEXT_LABELS[key]} readings`,
    points: (grouped.get(key) ?? []).sort((a, b) => a.t - b.t),
  }))

  const observedDays = new Set(series.flatMap((item) => item.points.map((point) => point.day)))
  const missingDays: number[] = []
  for (let day = range.fromDay; day <= range.toDay; day += 1) if (!observedDays.has(day)) missingDays.push(day)

  return {
    metric,
    series,
    emptyRecords: emptyRecords.sort((a, b) => a.t - b.t),
    missingDays,
    observationCount: series.reduce((count, item) => count + item.points.length, 0),
  }
}

/**
 * Cuts a series into runs that may be joined by a line. A run ends where a whole mission day
 * has no value, or where a record of the same series exists without one.
 */
export function splitIntoRuns(series: MetricSeries, emptyRecords: EmptyRecord[]): SeriesPoint[][] {
  const runs: SeriesPoint[][] = []
  let current: SeriesPoint[] = []
  for (const point of series.points) {
    const previous = current.at(-1)
    const broken =
      previous !== undefined &&
      (point.day - previous.day > 1 ||
        emptyRecords.some((empty) => empty.seriesKey === series.key && empty.t > previous.t && empty.t < point.t))
    if (broken) {
      runs.push(current)
      current = []
    }
    current.push(point)
  }
  if (current.length > 0) runs.push(current)
  return runs
}

/** "Day 7" or "Days 3, 4 and 7" */
export function formatDayList(days: number[]): string {
  if (days.length === 0) return ''
  if (days.length === 1) return `Day ${days[0]}`
  return `Days ${days.slice(0, -1).join(', ')} and ${days.at(-1)}`
}
