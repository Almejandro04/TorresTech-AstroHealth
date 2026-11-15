/**
 * In-memory implementation of the contract v0.1.0 selection rules over the synthetic seed.
 * Pure functions over a store, with no timers and no browser APIs, so `npm run check:mocks`
 * can compare their output with docs/examples/api_examples.json.
 *
 * Contract rules implemented here: observation cutoff (`as_of`), mission-day arithmetic in UTC,
 * latest non-null value per indicator, one journal entry per astronaut and day, and alert
 * visibility at a cutoff.
 *
 * MOCK-ONLY POLICIES (not backend rules; BACKEND-04/05 and DATA-06 own the real ones):
 *  - References use the method the shared fixtures name, `fixture_reference_mean`, over the
 *    window those fixtures declare (mission days 1-5, rest context for vitals).
 *  - A reference is `available` once that window has closed at the cutoff and holds at least
 *    one value; before that it is `insufficient_data`.
 *  - Alert evaluation is `available` when at least one reference is available.
 */
import type {
  AlertListResponse,
  ApiErrorDetail,
  ApiResponse,
  Astronaut,
  BaselineMetric,
  BaselineMetricName,
  EvaluationStatus,
  HealthAlert,
  HealthJournal,
  HealthJournalInput,
  HealthReading,
  HealthSummary,
  MeasurementContext,
  MetricSnapshot,
  MetricUnit,
  PaginatedResponse,
  PaginationMeta,
  Severity,
} from '../../types/health'
import { HealthDataError } from '../errors'
import type { AlertQuery, CutoffQuery, HistoryQuery, JournalWriteResult } from '../healthDataSource'
import { contractAlert, presentationAlerts } from './alertFixtures'
import { seedAstronauts, seedJournal, seedReadings } from './seed'

const SCHEMA_VERSION = '0.1.0' as const
const DAY_MS = 86_400_000
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/

export const MOCK_REFERENCE = { firstDay: 1, lastDay: 5, method: 'fixture_reference_mean' } as const

export type MockAnalysisMode = 'contract' | 'samples' | 'not_implemented'

export interface MockStore {
  astronauts: Astronaut[]
  readings: HealthReading[]
  journal: HealthJournal[]
  journalCounter: number
}

const recordId = (prefix: string, index: number) => `${prefix}-${String(index).padStart(4, '0')}`

export function createSeedStore(): MockStore {
  return {
    astronauts: structuredClone(seedAstronauts),
    readings: seedReadings.map((reading, index) => ({ ...reading, reading_id: recordId('READING', index + 1) })),
    journal: seedJournal.map((entry, index) => ({ ...entry, journal_id: recordId('JOURNAL', index + 1) })),
    journalCounter: seedJournal.length,
  }
}

// ---------------------------------------------------------------------------------------------
// Time and validation helpers

const toMs = (timestamp: string) => Date.parse(timestamp)
const dayStartMs = (astronaut: Astronaut, day: number) =>
  Date.parse(`${astronaut.mission_start_date}T00:00:00Z`) + (day - 1) * DAY_MS
const toIsoSeconds = (ms: number) => new Date(ms).toISOString().replace('.000Z', 'Z')
const dayEndIso = (astronaut: Astronaut, day: number) => toIsoSeconds(dayStartMs(astronaut, day) + DAY_MS - 1000)

export function missionDayAt(astronaut: Astronaut, timestamp: string): number {
  return Math.floor((toMs(timestamp) - dayStartMs(astronaut, 1)) / DAY_MS) + 1
}

function validationError(details: ApiErrorDetail[]): HealthDataError {
  return new HealthDataError({
    kind: 'validation',
    status: 422,
    code: 'VALIDATION_ERROR',
    message: 'Request validation failed.',
    details,
  })
}

function requireAstronaut(store: MockStore, astronautId: string): Astronaut {
  const astronaut = store.astronauts.find((candidate) => candidate.astronaut_id === astronautId)
  if (!astronaut) {
    throw new HealthDataError({
      kind: 'not_found',
      status: 404,
      code: 'ASTRONAUT_NOT_FOUND',
      message: `Astronaut ${astronautId} was not found.`,
    })
  }
  return astronaut
}

const isUtcTimestamp = (value: unknown): value is string =>
  typeof value === 'string' && UTC_TIMESTAMP.test(value) && !Number.isNaN(Date.parse(value))

/** Explicit cutoffs must fall inside the mission; an absent one resolves to the latest record. */
function resolveCutoff(store: MockStore, astronaut: Astronaut, asOf: string | undefined): string | null {
  if (asOf !== undefined) {
    if (!isUtcTimestamp(asOf)) {
      throw validationError([{ field: 'query.as_of', message: 'Must be a UTC timestamp ending in Z.' }])
    }
    const day = missionDayAt(astronaut, asOf)
    if (day < 1 || day > astronaut.planned_duration_days) {
      throw validationError([{ field: 'query.as_of', message: 'Must be within the mission.' }])
    }
    return asOf
  }
  let latest: string | null = null
  for (const record of [...store.readings, ...store.journal]) {
    if (record.astronaut_id !== astronaut.astronaut_id) continue
    if (latest === null || toMs(record.timestamp) > toMs(latest)) latest = record.timestamp
  }
  return latest
}

const atOrBefore = (timestamp: string, cutoff: string | null) => cutoff !== null && toMs(timestamp) <= toMs(cutoff)

function byTimeThenId<T extends { timestamp: string }>(idOf: (record: T) => string) {
  return (a: T, b: T) => toMs(a.timestamp) - toMs(b.timestamp) || idOf(a).localeCompare(idOf(b))
}

function visibleReadings(store: MockStore, astronaut: Astronaut, cutoff: string | null): HealthReading[] {
  return store.readings
    .filter((reading) => reading.astronaut_id === astronaut.astronaut_id && atOrBefore(reading.timestamp, cutoff))
    .sort(byTimeThenId((reading) => reading.reading_id))
}

function visibleJournal(store: MockStore, astronaut: Astronaut, cutoff: string | null): HealthJournal[] {
  return store.journal
    .filter((entry) => entry.astronaut_id === astronaut.astronaut_id && atOrBefore(entry.timestamp, cutoff))
    .sort(byTimeThenId((entry) => entry.journal_id))
}

function validatedDayRange(astronaut: Astronaut, query: HistoryQuery): { from: number; to: number } {
  const details: ApiErrorDetail[] = []
  const check = (value: number | undefined, field: string) => {
    if (value === undefined) return
    if (!Number.isInteger(value) || value < 1 || value > astronaut.planned_duration_days) {
      details.push({ field, message: 'Must be a mission day within the planned duration.' })
    }
  }
  check(query.from_day, 'query.from_day')
  check(query.to_day, 'query.to_day')
  if (query.from_day !== undefined && query.to_day !== undefined && query.from_day > query.to_day) {
    details.push({ field: 'query.from_day', message: 'Must not be after to_day.' })
  }
  if (details.length > 0) throw validationError(details)
  return { from: query.from_day ?? 1, to: query.to_day ?? astronaut.planned_duration_days }
}

function paginate<T>(records: T[], query: HistoryQuery, asOf: string | null): PaginatedResponse<T> {
  const limit = query.limit ?? 100
  const offset = query.offset ?? 0
  const details: ApiErrorDetail[] = []
  if (!Number.isInteger(limit) || limit < 1 || limit > 1000) details.push({ field: 'query.limit', message: 'Must be between 1 and 1000.' })
  if (!Number.isInteger(offset) || offset < 0) details.push({ field: 'query.offset', message: 'Must be 0 or greater.' })
  if (details.length > 0) throw validationError(details)
  const meta: PaginationMeta = { schema_version: SCHEMA_VERSION, as_of: asOf, total: records.length, limit, offset }
  return { data: records.slice(offset, offset + limit), meta }
}

// ---------------------------------------------------------------------------------------------
// Reads

export function listAstronauts(store: MockStore): PaginatedResponse<Astronaut> {
  const sorted = [...store.astronauts].sort((a, b) => a.astronaut_id.localeCompare(b.astronaut_id))
  return paginate(sorted, {}, null)
}

export function listReadings(store: MockStore, astronautId: string, query: HistoryQuery = {}): PaginatedResponse<HealthReading> {
  const astronaut = requireAstronaut(store, astronautId)
  const cutoff = resolveCutoff(store, astronaut, query.as_of)
  const { from, to } = validatedDayRange(astronaut, query)
  const records = visibleReadings(store, astronaut, cutoff).filter((r) => r.mission_day >= from && r.mission_day <= to)
  return paginate(records, query, cutoff)
}

export function listJournal(store: MockStore, astronautId: string, query: HistoryQuery = {}): PaginatedResponse<HealthJournal> {
  const astronaut = requireAstronaut(store, astronautId)
  const cutoff = resolveCutoff(store, astronaut, query.as_of)
  const { from, to } = validatedDayRange(astronaut, query)
  const records = visibleJournal(store, astronaut, cutoff).filter((e) => e.mission_day >= from && e.mission_day <= to)
  return paginate(records, query, cutoff)
}

const emptySnapshot = (unit: MetricUnit): MetricSnapshot => ({
  value: null,
  unit,
  timestamp: null,
  mission_day: null,
  measurement_context: null,
  source_type: null,
  source_id: null,
  record_id: null,
})

/** Latest non-null observation of one indicator; records arrive sorted by (timestamp, id). */
function latestSnapshot<T extends { timestamp: string; mission_day: number; source_type: 'synthetic'; source_id: string }>(
  records: T[],
  unit: MetricUnit,
  valueOf: (record: T) => number | null,
  idOf: (record: T) => string,
  contextOf: (record: T) => MeasurementContext | null,
): MetricSnapshot {
  for (let index = records.length - 1; index >= 0; index -= 1) {
    const record = records[index]
    if (!record) continue
    const value = valueOf(record)
    if (value === null) continue
    return {
      value,
      unit,
      timestamp: record.timestamp,
      mission_day: record.mission_day,
      measurement_context: contextOf(record),
      source_type: record.source_type,
      source_id: record.source_id,
      record_id: idOf(record),
    }
  }
  return emptySnapshot(unit)
}

function buildBaselines(
  astronaut: Astronaut,
  readings: HealthReading[],
  journal: HealthJournal[],
  cutoff: string | null,
  mode: MockAnalysisMode,
): Record<BaselineMetricName, BaselineMetric> {
  const referenceStart = toIsoSeconds(dayStartMs(astronaut, MOCK_REFERENCE.firstDay))
  const referenceEnd = dayEndIso(astronaut, MOCK_REFERENCE.lastDay)
  const windowClosed = cutoff !== null && toMs(cutoff) >= toMs(referenceEnd)
  const inWindow = (record: { mission_day: number }) =>
    record.mission_day >= MOCK_REFERENCE.firstDay && record.mission_day <= MOCK_REFERENCE.lastDay

  const build = (values: (number | null)[], context: MeasurementContext | null): BaselineMetric => {
    if (mode === 'not_implemented') {
      return { status: 'not_implemented', value: null, sample_count: 0, reference_start: null, reference_end: null, measurement_context: context, method: null }
    }
    const samples = values.filter((value): value is number => value !== null)
    if (!windowClosed || samples.length === 0) {
      return { status: 'insufficient_data', value: null, sample_count: samples.length, reference_start: null, reference_end: null, measurement_context: context, method: null }
    }
    const mean = samples.reduce((sum, value) => sum + value, 0) / samples.length
    return {
      status: 'available',
      value: Math.round(mean * 10) / 10,
      sample_count: samples.length,
      reference_start: referenceStart,
      reference_end: referenceEnd,
      measurement_context: context,
      method: MOCK_REFERENCE.method,
    }
  }

  const restReadings = readings.filter((reading) => inWindow(reading) && reading.measurement_context === 'rest')
  const windowJournal = journal.filter(inWindow)
  return {
    heart_rate_bpm: build(restReadings.map((r) => r.heart_rate_bpm), 'rest'),
    spo2_percent: build(restReadings.map((r) => r.spo2_percent), 'rest'),
    respiratory_rate_bpm: build(restReadings.map((r) => r.respiratory_rate_bpm), 'rest'),
    sleep_hours_last_night: build(windowJournal.map((e) => e.sleep_hours_last_night), null),
  }
}

function evaluationStatus(baselines: Record<BaselineMetricName, BaselineMetric>, mode: MockAnalysisMode): EvaluationStatus {
  if (mode === 'not_implemented') return 'not_implemented'
  return Object.values(baselines).some((baseline) => baseline.status === 'available') ? 'available' : 'insufficient_data'
}

/** Alerts detected at or before the cutoff. One resolved later still reads as active in that view. */
function alertsAt(astronaut: Astronaut, cutoff: string | null, status: EvaluationStatus, mode: MockAnalysisMode): HealthAlert[] {
  if (status !== 'available' || cutoff === null) return []
  const pool = mode === 'samples' ? [contractAlert, ...presentationAlerts] : [contractAlert]
  return pool
    .filter((alert) => alert.astronaut_id === astronaut.astronaut_id && toMs(alert.timestamp) <= toMs(cutoff))
    .map((alert): HealthAlert =>
      alert.resolved_at !== null && toMs(alert.resolved_at) > toMs(cutoff)
        ? { ...alert, status: 'active', resolved_at: null }
        : { ...alert },
    )
    .sort((a, b) => toMs(b.timestamp) - toMs(a.timestamp) || a.alert_id.localeCompare(b.alert_id))
}

const SEVERITY_RANK: Record<Severity, number> = { info: 1, warning: 2, critical: 3 }

export function buildSummary(
  store: MockStore,
  astronautId: string,
  query: CutoffQuery = {},
  mode: MockAnalysisMode = 'contract',
): ApiResponse<HealthSummary> {
  const astronaut = requireAstronaut(store, astronautId)
  const cutoff = resolveCutoff(store, astronaut, query.as_of)
  const readings = visibleReadings(store, astronaut, cutoff)
  const journal = visibleJournal(store, astronaut, cutoff)
  const baselines = buildBaselines(astronaut, readings, journal, cutoff, mode)
  const status = evaluationStatus(baselines, mode)
  const active = alertsAt(astronaut, cutoff, status, mode).filter((alert) => alert.status === 'active')
  const highest = active.reduce<Severity | null>(
    (top, alert) => (top === null || SEVERITY_RANK[alert.severity] > SEVERITY_RANK[top] ? alert.severity : top),
    null,
  )
  const readingId = (reading: HealthReading) => reading.reading_id
  const readingContext = (reading: HealthReading) => reading.measurement_context
  const journalId = (entry: HealthJournal) => entry.journal_id

  const data: HealthSummary = {
    astronaut: { ...astronaut },
    mission_day: cutoff === null ? null : missionDayAt(astronaut, cutoff),
    latest_reading: readings.at(-1) ?? null,
    latest_journal: journal.at(-1) ?? null,
    latest_metrics: {
      heart_rate_bpm: latestSnapshot(readings, 'beats/min', (r) => r.heart_rate_bpm, readingId, readingContext),
      spo2_percent: latestSnapshot(readings, '%', (r) => r.spo2_percent, readingId, readingContext),
      respiratory_rate_bpm: latestSnapshot(readings, 'breaths/min', (r) => r.respiratory_rate_bpm, readingId, readingContext),
      sleep_hours_last_night: latestSnapshot(journal, 'hours', (e) => e.sleep_hours_last_night, journalId, () => null),
      mood_score: latestSnapshot(journal, 'score', (e) => e.mood_score, journalId, () => null),
    },
    baselines,
    alert_summary:
      status === 'available'
        ? { evaluation_status: status, active_count: active.length, highest_severity: highest, recent: active.slice(0, 3) }
        : { evaluation_status: status, active_count: null, highest_severity: null, recent: [] },
  }
  return { data, meta: { schema_version: SCHEMA_VERSION, as_of: cutoff } }
}

export function listAlerts(
  store: MockStore,
  astronautId: string,
  query: AlertQuery = {},
  mode: MockAnalysisMode = 'contract',
): AlertListResponse {
  const astronaut = requireAstronaut(store, astronautId)
  const cutoff = resolveCutoff(store, astronaut, query.as_of)
  const { from, to } = validatedDayRange(astronaut, query)
  const baselines = buildBaselines(astronaut, visibleReadings(store, astronaut, cutoff), visibleJournal(store, astronaut, cutoff), cutoff, mode)
  const status = evaluationStatus(baselines, mode)
  const alerts = alertsAt(astronaut, cutoff, status, mode).filter(
    (alert) => alert.mission_day >= from && alert.mission_day <= to && (query.status === undefined || alert.status === query.status),
  )
  const page = paginate(alerts, query, cutoff)
  return { data: page.data, meta: { ...page.meta, evaluation_status: status } }
}

// ---------------------------------------------------------------------------------------------
// Journal write (one entry per astronaut and mission day; a repost updates and keeps the ID)

function validateJournalInput(astronaut: Astronaut, input: HealthJournalInput): { notes: string | null } {
  const details: ApiErrorDetail[] = []
  const { sleep_hours_last_night: sleep, mood_score: mood } = input

  if (!isUtcTimestamp(input.timestamp)) {
    details.push({ field: 'body.timestamp', message: 'Must be a UTC timestamp ending in Z.' })
  }
  if (!Number.isInteger(input.mission_day) || input.mission_day < 1 || input.mission_day > astronaut.planned_duration_days) {
    details.push({ field: 'body.mission_day', message: 'Must be a mission day within the planned duration.' })
  } else if (isUtcTimestamp(input.timestamp) && missionDayAt(astronaut, input.timestamp) !== input.mission_day) {
    details.push({ field: 'body.mission_day', message: 'Does not match the observation UTC date.' })
  }
  if (sleep !== null && (typeof sleep !== 'number' || !Number.isFinite(sleep) || sleep < 0 || sleep > 24)) {
    details.push({ field: 'body.sleep_hours_last_night', message: 'Must be between 0 and 24.' })
  }
  if (mood !== null && (typeof mood !== 'number' || !Number.isInteger(mood) || mood < 1 || mood > 5)) {
    details.push({ field: 'body.mood_score', message: 'Must be an integer from 1 to 5.' })
  }
  if (input.notes !== null && typeof input.notes !== 'string') {
    details.push({ field: 'body.notes', message: 'Must be text or null.' })
  }
  const trimmed = typeof input.notes === 'string' ? input.notes.trim() : ''
  if (trimmed.length > 2000) details.push({ field: 'body.notes', message: 'Must be at most 2,000 characters.' })
  if (input.source_type !== 'synthetic') details.push({ field: 'body.source_type', message: 'Must be synthetic.' })
  if (typeof input.source_id !== 'string' || input.source_id.length === 0) {
    details.push({ field: 'body.source_id', message: 'Must identify a source manifest.' })
  }
  const notes = trimmed.length > 0 ? trimmed : null
  if (details.length === 0 && sleep === null && mood === null && notes === null) {
    details.push({ field: 'body', message: 'Provide sleep, mood, or a note.' })
  }
  if (details.length > 0) throw validationError(details)
  return { notes }
}

export function upsertJournal(store: MockStore, astronautId: string, input: HealthJournalInput): JournalWriteResult {
  const astronaut = requireAstronaut(store, astronautId)
  const { notes } = validateJournalInput(astronaut, input)
  const fields: HealthJournalInput = { ...input, notes }
  const index = store.journal.findIndex(
    (entry) => entry.astronaut_id === astronautId && entry.mission_day === input.mission_day,
  )
  const existing = index === -1 ? undefined : store.journal[index]

  let saved: HealthJournal
  if (existing) {
    saved = { ...fields, journal_id: existing.journal_id, astronaut_id: astronautId }
    store.journal[index] = saved
  } else {
    store.journalCounter += 1
    saved = { ...fields, journal_id: recordId('JOURNAL', store.journalCounter), astronaut_id: astronautId }
    store.journal.push(saved)
  }
  return {
    outcome: existing ? 'updated' : 'created',
    response: { data: { ...saved }, meta: { schema_version: SCHEMA_VERSION, as_of: resolveCutoff(store, astronaut, undefined) } },
  }
}
