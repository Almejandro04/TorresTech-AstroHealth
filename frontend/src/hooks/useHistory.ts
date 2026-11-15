import type { HealthDataSource, HistoryQuery } from '../services'
import type { DayRange } from '../lib/series'
import type { HealthJournal, HealthReading, PaginatedResponse } from '../types/health'
import { useMission } from './MissionContext'
import { useResource } from './useResource'
import type { Resource } from './useResource'

export interface MissionHistory {
  readings: HealthReading[]
  journal: HealthJournal[]
}

const PAGE_SIZE = 1000

/** Follows the contract's pagination until the whole filtered list has been read. */
async function readAll<T>(fetchPage: (query: HistoryQuery) => Promise<PaginatedResponse<T>>, query: HistoryQuery): Promise<T[]> {
  const records: T[] = []
  for (;;) {
    const page = await fetchPage({ ...query, limit: PAGE_SIZE, offset: records.length })
    records.push(...page.data)
    if (page.data.length === 0 || records.length >= page.meta.total) return records
  }
}

export function loadHistory(source: HealthDataSource, astronautId: string, query: HistoryQuery): Promise<MissionHistory> {
  return Promise.all([
    readAll((page) => source.getReadings(astronautId, page), query),
    readAll((page) => source.getJournal(astronautId, page), query),
  ]).then(([readings, journal]) => ({ readings, journal }))
}

/**
 * Readings and journal entries for a mission-day range, at the mission view's cutoff.
 * The two cadences stay separate: vital readings are point-in-time, the journal is daily.
 */
export function useHistory(range: DayRange | null): Resource<MissionHistory> {
  const { source, astronaut, asOf, revision, view } = useMission()
  const ready = astronaut !== null && range !== null && view.status === 'ready'
  const key = ready ? `history:${astronaut.astronaut_id}:${asOf ?? 'latest'}:${range.fromDay}-${range.toDay}` : null
  return useResource(
    key,
    () => loadHistory(source, astronaut?.astronaut_id ?? '', { as_of: asOf, from_day: range?.fromDay, to_day: range?.toDay }),
    revision,
  )
}
