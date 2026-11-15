import { useMission } from './MissionContext'
import { useResource } from './useResource'
import type { Resource } from './useResource'
import type { DayRange } from '../lib/series'
import { loadHistory } from '../services/history'
import type { MissionHistory } from '../services/history'

// Retain the public imports used by the existing pages.
export { loadHistory } from '../services/history'
export type { MissionHistory } from '../services/history'

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
