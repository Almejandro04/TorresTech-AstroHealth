import type { HealthDataSource, HistoryQuery } from './healthDataSource'
import { HealthDataError } from './errors'
import type { HealthJournal, HealthReading, PaginatedResponse } from '../types/health'

export interface MissionHistory {
  readings: HealthReading[]
  journal: HealthJournal[]
}

const PAGE_SIZE = 1000

/** Follows the contract's pagination until the whole filtered list has been read. */
async function readAll<T>(fetchPage: (query: HistoryQuery) => Promise<PaginatedResponse<T>>, query: HistoryQuery): Promise<T[]> {
  const records: T[] = []
  let total: number | undefined
  for (;;) {
    const page = await fetchPage({ ...query, limit: PAGE_SIZE, offset: records.length })
    if (page.meta.offset !== records.length ||
        (total !== undefined && page.meta.total !== total) ||
        page.meta.total < records.length + page.data.length ||
        (page.data.length === 0 && records.length < page.meta.total)) {
      throw new HealthDataError({ kind: 'server', code: 'INCONSISTENT_HISTORY', message: 'The history changed or a page was missing. Reload this view to try again.' })
    }
    total = page.meta.total
    records.push(...page.data)
    if (records.length >= total) return records
  }
}

export function loadHistory(source: HealthDataSource, astronautId: string, query: HistoryQuery): Promise<MissionHistory> {
  return Promise.all([
    readAll((page) => source.getReadings(astronautId, page), query),
    readAll((page) => source.getJournal(astronautId, page), query),
  ]).then(([readings, journal]) => ({ readings, journal }))
}

