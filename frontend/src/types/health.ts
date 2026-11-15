/** Shared API contract v0.1.0: see the repository's docs/api_contract.md. */
export type MeasurementContext = 'rest' | 'exercise' | 'sleep' | 'unknown'
export type EvaluationStatus = 'available' | 'insufficient_data' | 'not_implemented'
export type MoodScore = 1 | 2 | 3 | 4 | 5
export type Severity = 'info' | 'warning' | 'critical'
export type MetricUnit = 'beats/min' | '%' | 'breaths/min' | 'hours' | 'score'
export type MetricName = 'heart_rate_bpm' | 'spo2_percent' | 'respiratory_rate_bpm' | 'sleep_hours_last_night' | 'mood_score'
export type BaselineMetricName = Exclude<MetricName, 'mood_score'>

export interface ApiMeta {
  schema_version: '0.1.0'
  as_of: string | null
}

export interface PaginationMeta extends ApiMeta {
  total: number
  limit: number
  offset: number
}

export interface ApiResponse<T, M extends ApiMeta = ApiMeta> {
  data: T
  meta: M
}

export type PaginatedResponse<T> = ApiResponse<T[], PaginationMeta>

export interface ApiErrorResponse {
  error: {
    code: string
    message: string
    details: { field: string; message: string }[]
  }
  meta: ApiMeta
}

export interface Astronaut {
  astronaut_id: string
  name: string
  is_fictional: true
  mission_start_date: string
  planned_duration_days: number
}

export interface HealthReadingInput {
  timestamp: string
  mission_day: number
  heart_rate_bpm: number | null
  spo2_percent: number | null
  respiratory_rate_bpm: number | null
  measurement_context: MeasurementContext
  source_type: 'synthetic'
  source_id: string
}

export interface HealthReading extends HealthReadingInput {
  reading_id: string
  astronaut_id: string
}

export interface HealthJournalInput {
  timestamp: string
  mission_day: number
  sleep_hours_last_night: number | null
  mood_score: MoodScore | null
  notes: string | null
  source_type: 'synthetic'
  source_id: string
}

export interface HealthJournal extends HealthJournalInput {
  journal_id: string
  astronaut_id: string
}

export interface HealthAlert {
  alert_id: string
  astronaut_id: string
  timestamp: string
  mission_day: number
  indicator: MetricName
  severity: Severity
  status: 'active' | 'resolved'
  description: string
  explanation: string
  rule_id: string
  rule_version: string
  observed_value: number
  baseline_value: number | null
  unit: MetricUnit
  window_start: string
  window_end: string
  resolved_at: string | null
  source_type: 'synthetic'
  source_id: string
}

export interface MetricSnapshot {
  value: number | null
  unit: MetricUnit
  timestamp: string | null
  mission_day: number | null
  measurement_context: MeasurementContext | null
  source_type: 'synthetic' | null
  source_id: string | null
  record_id: string | null
}

export interface BaselineMetric {
  status: EvaluationStatus
  value: number | null
  sample_count: number
  reference_start: string | null
  reference_end: string | null
  measurement_context: MeasurementContext | null
  method: string | null
}

export interface HealthSummary {
  astronaut: Astronaut
  mission_day: number | null
  latest_reading: HealthReading | null
  latest_journal: HealthJournal | null
  latest_metrics: Record<MetricName, MetricSnapshot>
  baselines: Record<BaselineMetricName, BaselineMetric>
  alert_summary: {
    evaluation_status: EvaluationStatus
    active_count: number | null
    highest_severity: Severity | null
    recent: HealthAlert[]
  }
}

export type AlertStatus = HealthAlert['status']
export type ApiErrorDetail = ApiErrorResponse['error']['details'][number]

export interface AlertListMeta extends PaginationMeta {
  evaluation_status: EvaluationStatus
}

export type AlertListResponse = ApiResponse<HealthAlert[], AlertListMeta>
