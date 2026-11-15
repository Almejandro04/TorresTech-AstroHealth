/** Runtime guards for the v0.1.0 wire format, not physiological interpretation. */
type ObjectValue = Record<string, unknown>
type Guard = (value: unknown) => boolean
const object = (v: unknown): v is ObjectValue => typeof v === 'object' && v !== null && !Array.isArray(v)
const text: Guard = v => typeof v === 'string' && v.length > 0
const number: Guard = v => typeof v === 'number' && Number.isFinite(v)
const integer: Guard = v => number(v) && Number.isInteger(v) && Number(v) >= 0
const day: Guard = v => integer(v) && Number(v) >= 1
const nullable = (guard: Guard): Guard => v => v === null || guard(v)
const oneOf = (...values: unknown[]): Guard => v => values.includes(v)
const array = (guard: Guard): Guard => v => Array.isArray(v) && v.every(guard)
const shape = (fields: Record<string, Guard>): Guard => v => object(v) && Object.entries(fields).every(([key, guard]) => guard(v[key]))
const utc: Guard = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(v) && Number.isFinite(Date.parse(v))
const context = oneOf('rest', 'exercise', 'sleep', 'unknown')
const evaluation = oneOf('available', 'insufficient_data', 'not_implemented')
const severity = oneOf('info', 'warning', 'critical')
const metric = oneOf('heart_rate_bpm', 'spo2_percent', 'respiratory_rate_bpm', 'sleep_hours_last_night', 'mood_score')
const meta = shape({ schema_version: oneOf('0.1.0'), as_of: nullable(utc) })
const pagination = shape({ schema_version: oneOf('0.1.0'), as_of: nullable(utc), total: integer, limit: v => day(v) && Number(v) <= 1000, offset: integer })
const source = { astronaut_id: text, timestamp: utc, mission_day: day, source_type: oneOf('synthetic'), source_id: text }

export const astronaut = shape({ astronaut_id: text, name: text, is_fictional: oneOf(true), mission_start_date: v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)), planned_duration_days: day })
export const reading = shape({ ...source, reading_id: text, heart_rate_bpm: nullable(number), spo2_percent: nullable(number), respiratory_rate_bpm: nullable(number), measurement_context: context })
export const journal = shape({ ...source, journal_id: text, sleep_hours_last_night: nullable(v => number(v) && Number(v) >= 0 && Number(v) <= 24), mood_score: nullable(oneOf(1, 2, 3, 4, 5)), notes: nullable(v => typeof v === 'string' && v.length <= 2000) })
const alert = shape({ ...source, alert_id: text, indicator: metric, severity, status: oneOf('active', 'resolved'), description: text, explanation: text, rule_id: text, rule_version: text, observed_value: number, baseline_value: nullable(number), unit: oneOf('beats/min', '%', 'breaths/min', 'hours', 'score'), window_start: utc, window_end: utc, resolved_at: nullable(utc) })
const snapshot = (unit: string): Guard => shape({ value: nullable(number), unit: oneOf(unit), timestamp: nullable(utc), mission_day: nullable(day), measurement_context: nullable(context), source_type: nullable(oneOf('synthetic')), source_id: nullable(text), record_id: nullable(text) })
const baseline = shape({ status: evaluation, value: nullable(number), sample_count: integer, reference_start: nullable(utc), reference_end: nullable(utc), measurement_context: nullable(context), method: nullable(text) })
const summary = shape({
  astronaut, mission_day: nullable(day), latest_reading: nullable(reading), latest_journal: nullable(journal),
  latest_metrics: shape({ heart_rate_bpm: snapshot('beats/min'), spo2_percent: snapshot('%'), respiratory_rate_bpm: snapshot('breaths/min'), sleep_hours_last_night: snapshot('hours'), mood_score: snapshot('score') }),
  baselines: shape({ heart_rate_bpm: baseline, spo2_percent: baseline, respiratory_rate_bpm: baseline, sleep_hours_last_night: baseline }),
  alert_summary: shape({ evaluation_status: evaluation, active_count: nullable(integer), highest_severity: nullable(severity), recent: array(alert) }),
})
const page = (item: Guard, extra: Record<string, Guard> = {}): Guard => v =>
  shape({ data: array(item), meta: shape({ schema_version: oneOf('0.1.0'), as_of: nullable(utc), total: integer, limit: v => day(v) && Number(v) <= 1000, offset: integer, ...extra }) })(v) &&
  object(v) && object(v.meta) && Array.isArray(v.data) && pagination(v.meta) && v.data.length <= Number(v.meta.limit) && (v.data.length === 0 || Number(v.meta.total) >= Number(v.meta.offset) + v.data.length)

export const responses = {
  health: shape({ data: shape({ status: oneOf('ok'), service: oneOf('astrohealth-api') }), meta }),
  astronauts: page(astronaut), readings: page(reading), journal: page(journal),
  summary: shape({ data: summary, meta }), alerts: page(alert, { evaluation_status: evaluation }),
  savedJournal: shape({ data: journal, meta }),
  savedReading: shape({ data: reading, meta }),
}

/** Do not present another profile or a future observation as the requested view. */
export function matchesView(value: unknown, astronautId: string, cutoff?: string): boolean {
  if (!object(value)) return false
  const responseCutoff = object(value.meta) && typeof value.meta.as_of === 'string' ? Date.parse(value.meta.as_of) : -Infinity
  const cutoffMs = cutoff ? Math.min(Date.parse(cutoff), responseCutoff) : responseCutoff
  function visit(node: unknown): boolean {
    if (Array.isArray(node)) return node.every(visit)
    if (!object(node)) return true
    if ('astronaut_id' in node && node.astronaut_id !== astronautId) return false
    for (const [key, child] of Object.entries(node)) {
      if (['timestamp', 'as_of', 'reference_end', 'window_end', 'resolved_at'].includes(key) && typeof child === 'string' && Date.parse(child) > cutoffMs) return false
      if (!visit(child)) return false
    }
    return true
  }
  return visit(value)
}

export function errorDetails(value: unknown): { code: string | null; message: string; details: { field: string; message: string }[] } {
  if (!object(value) || !object(value.error)) return { code: null, message: 'The API request failed.', details: [] }
  const e = value.error
  return {
    code: typeof e.code === 'string' ? e.code : null,
    message: typeof e.message === 'string' ? e.message : 'The API request failed.',
    details: Array.isArray(e.details) ? e.details.filter((d): d is { field: string; message: string } => object(d) && typeof d.field === 'string' && typeof d.message === 'string') : [],
  }
}
