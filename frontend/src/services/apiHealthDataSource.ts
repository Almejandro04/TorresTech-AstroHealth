import { HealthDataError } from './errors'
import type { HealthDataSource, HistoryQuery, JournalWriteResult } from './healthDataSource'
import type { ApiResponse } from '../types/health'
import { errorDetails, matchesView, responses } from './responseValidation'

type HealthResponse = ApiResponse<{ status: 'ok'; service: 'astrohealth-api' }>
type Query = HistoryQuery & { status?: string }
interface Options { baseUrl: string; timeoutMs?: number; fetch?: typeof globalThis.fetch }

export function validateApiBaseUrl(raw: string): string {
  const url = new URL(raw)
  if (!['http:', 'https:'].includes(url.protocol) || url.search || url.hash || url.username || url.password) {
    throw new Error('API base URL must use HTTP(S) without credentials, query or fragment.')
  }
  return url.href.replace(/\/+$/, '')
}

/** Real HTTP transport only. Failures never fall back to the in-memory demo. */
export function createApiHealthDataSource(options: Options): HealthDataSource & { getHealth(): Promise<HealthResponse> } {
  const baseUrl = validateApiBaseUrl(options.baseUrl)
  const timeoutMs = options.timeoutMs ?? 10000
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new Error('API timeout must be a positive number of milliseconds.')
  const fetcher = options.fetch ?? globalThis.fetch.bind(globalThis)

  async function request<T>(path: string, guard: (v: unknown) => boolean, query: Query = {}, body?: unknown, identity?: string): Promise<{ data: T; status: number }> {
    const url = new URL(baseUrl + path)
    for (const [key, value] of Object.entries(query)) if (value !== undefined) url.searchParams.set(key, String(value))
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const write = body !== undefined
    let response: Response | undefined
    try {
      response = await fetcher(url, {
        method: write ? 'POST' : 'GET', credentials: 'omit', cache: 'no-store', signal: controller.signal,
        headers: write ? { Accept: 'application/json', 'Content-Type': 'application/json' } : { Accept: 'application/json' },
        ...(write ? { body: JSON.stringify(body) } : {}),
      })
      let value: unknown
      try { value = await response.json() } catch {
        if (controller.signal.aborted) throw new Error('Response deadline exceeded.')
        if (response.ok) throw new HealthDataError({ kind: write ? 'timeout' : 'server', status: response.status, code: 'INVALID_RESPONSE', message: 'The API response was not valid JSON; the result cannot be confirmed.' })
      }
      if (!response.ok) {
        const details = errorDetails(value)
        // A missing endpoint (the bootstrap API has only /health) is not an unknown astronaut.
        const kind = response.status === 404 && details.code === 'ASTRONAUT_NOT_FOUND' ? 'not_found' : response.status === 422 ? 'validation' : response.status === 409 ? 'conflict' : write && response.status >= 500 ? 'timeout' : 'server'
        throw new HealthDataError({ kind, status: response.status, ...details })
      }
      const expectedStatus = write ? response.status === 200 || response.status === 201 : response.status === 200
      if (!expectedStatus || !guard(value) || (identity && !matchesView(value, identity, query.as_of))) {
        throw new HealthDataError({ kind: write ? 'timeout' : 'server', status: response.status, code: 'INVALID_RESPONSE', message: 'The API response does not match the requested v0.1.0 view.' })
      }
      return { data: value as T, status: response.status }
    } catch (error) {
      if (error instanceof HealthDataError) throw error
      // A failed POST may have been applied before the connection broke. Never promise that nothing was sent.
      throw new HealthDataError({ kind: write || controller.signal.aborted ? 'timeout' : 'network', message: write ? 'The save could not be confirmed.' : controller.signal.aborted ? 'The API response timed out.' : 'The API could not be reached.' })
    } finally { clearTimeout(timer) }
  }
  const profile = (id: string) => {
    if (!id || id === '.' || id === '..') throw new HealthDataError({ kind: 'validation', code: 'INVALID_PROFILE_ID', message: 'Choose a valid profile.' })
    return `/api/astronauts/${encodeURIComponent(id)}`
  }
  const read = async <T>(path: string, guard: (v: unknown) => boolean, query?: Query, id?: string): Promise<T> => (await request<T>(path, guard, query, undefined, id)).data
  return {
    kind: 'api',
    getHealth: () => read<HealthResponse>('/api/health', responses.health),
    getAstronauts: () => read('/api/astronauts', responses.astronauts, { limit: 1000 }),
    getSummary: async (id, query) => read(`${profile(id)}/summary`, responses.summary, query, id),
    getReadings: async (id, query) => read(`${profile(id)}/readings`, responses.readings, query, id),
    getJournal: async (id, query) => read(`${profile(id)}/journal`, responses.journal, query, id),
    getAlerts: async (id, query) => read(`${profile(id)}/alerts`, responses.alerts, query, id),
    async saveJournal(id, entry): Promise<JournalWriteResult> {
      const result = await request<JournalWriteResult['response']>(`${profile(id)}/journal`, responses.savedJournal, {}, entry, id)
      if (result.data.data.mission_day !== entry.mission_day || Date.parse(result.data.data.timestamp) !== Date.parse(entry.timestamp) || result.data.data.source_id !== entry.source_id) {
        throw new HealthDataError({ kind: 'timeout', code: 'INVALID_RESPONSE', status: result.status, message: 'The journal response does not confirm the requested day and source.' })
      }
      return { outcome: result.status === 201 ? 'created' : 'updated', response: result.data }
    },
  }
}
