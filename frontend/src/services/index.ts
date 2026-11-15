import type { HealthDataSource } from './healthDataSource'
import { mockHealthDataSource } from './mockHealthDataSource'
import { createApiHealthDataSource } from './apiHealthDataSource'
import { appConfig } from './config'

/**
 * Explicit data-source selection. The application never falls back from a failed live API to
 * mock data: FRONTEND-06 replaces this export with the FastAPI implementation of the same
 * interface, and a failure there is shown as a failure.
 */
export const healthDataSource: HealthDataSource = appConfig.dataSource === 'api'
  ? createApiHealthDataSource({ baseUrl: appConfig.apiBaseUrl, timeoutMs: appConfig.timeoutMs })
  : mockHealthDataSource

export { HealthDataError, toHealthDataError } from './errors'
export type { HealthDataErrorKind } from './errors'
export type { AlertQuery, CutoffQuery, HealthDataSource, HistoryQuery, JournalWriteResult } from './healthDataSource'
