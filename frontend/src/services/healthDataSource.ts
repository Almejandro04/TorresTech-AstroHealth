import type {
  AlertListResponse,
  AlertStatus,
  ApiResponse,
  Astronaut,
  HealthJournal,
  HealthJournalInput,
  HealthReading,
  HealthSummary,
  PaginatedResponse,
} from '../types/health'

/** `as_of` is the contract's observation cutoff. Omit it to let the source resolve the latest one. */
export interface CutoffQuery {
  as_of?: string
}

export interface HistoryQuery extends CutoffQuery {
  from_day?: number
  to_day?: number
  limit?: number
  offset?: number
}

export interface AlertQuery extends HistoryQuery {
  status?: AlertStatus
}

/** HTTP 201 maps to `created`; HTTP 200 (update or exact retry) maps to `updated`. */
export interface JournalWriteResult {
  outcome: 'created' | 'updated'
  response: ApiResponse<HealthJournal>
}

/**
 * The single boundary between views and data transport (contract v0.1.0).
 * FRONTEND-06 implements this same interface over FastAPI; views and hooks do not change.
 * Implementations reject with `HealthDataError`. POST /readings is not part of the four
 * views and is intentionally absent until a view needs it.
 */
export interface HealthDataSource {
  readonly kind: 'mock' | 'api'
  getAstronauts(): Promise<PaginatedResponse<Astronaut>>
  getSummary(astronautId: string, query?: CutoffQuery): Promise<ApiResponse<HealthSummary>>
  getReadings(astronautId: string, query?: HistoryQuery): Promise<PaginatedResponse<HealthReading>>
  getJournal(astronautId: string, query?: HistoryQuery): Promise<PaginatedResponse<HealthJournal>>
  getAlerts(astronautId: string, query?: AlertQuery): Promise<AlertListResponse>
  saveJournal(astronautId: string, entry: HealthJournalInput): Promise<JournalWriteResult>
}
