import { validateApiBaseUrl } from './apiHealthDataSource'

interface FrontendEnv {
  VITE_API_BASE_URL?: string
  VITE_DATA_SOURCE?: string
  VITE_API_TIMEOUT_MS?: string
  VITE_JOURNAL_SOURCE_ID?: string
  VITE_JOURNAL_TIME_UTC?: string
}

export function readAppConfig(env: FrontendEnv) {
  const apiBaseUrl = validateApiBaseUrl(env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000')
  const mode = env.VITE_DATA_SOURCE?.trim() || 'mock'
  if (mode !== 'mock' && mode !== 'api') throw new Error('VITE_DATA_SOURCE must be mock or api.')
  const timeoutMs = Number(env.VITE_API_TIMEOUT_MS || 10000)
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 120000) throw new Error('VITE_API_TIMEOUT_MS must be from 1 to 120000 milliseconds.')
  const sourceId = env.VITE_JOURNAL_SOURCE_ID?.trim()
  const timeUtc = env.VITE_JOURNAL_TIME_UTC?.trim()
  if (timeUtc && !/^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$/.test(timeUtc)) throw new Error('VITE_JOURNAL_TIME_UTC must be HH:MM:SS in UTC.')
  return { apiBaseUrl, dataSource: mode, timeoutMs, newJournalDefaults: sourceId && timeUtc ? { sourceId, timeUtc } : null }
}

export const appConfig = readAppConfig(import.meta.env)

/** Never used for mock reads. */
export function buildApiUrl(path: `/api/${string}`): string {
  return `${appConfig.apiBaseUrl}${path}`
}
