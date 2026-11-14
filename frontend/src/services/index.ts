import { mockHealthDataSource } from './mockHealthDataSource'
import type { HealthDataSource } from './healthDataSource'

/** Explicit mock default: the application does not silently fall back from a failed live API. */
export const healthDataSource: HealthDataSource = mockHealthDataSource
export type { HealthDataSource } from './healthDataSource'
