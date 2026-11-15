import { missionDayIsoDate } from '../lib/time'
import type { Astronaut, HealthJournal, HealthJournalInput, MoodScore } from '../types/health'

/**
 * INTEGRATION POINT (FRONTEND-05 / FRONTEND-06).
 * The contract requires an effective self-report time and a source manifest ID on every
 * journal entry. The constants below are mock-only defaults: 08:00 UTC on the mission day
 * and the synthetic seed manifest. API creates require explicit configuration from the
 * imported manifest; JournalPage enforces that gate and passes those defaults here.
 * A corrected entry always keeps its original time and source.
 */
export const NEW_ENTRY_TIME_UTC = '08:00:00'
export const NEW_ENTRY_SOURCE_ID = 'SYN-CORE-001'
export interface JournalDefaults { timeUtc: string; sourceId: string }

export interface JournalDraftValues {
  sleep: number | null
  mood: MoodScore | null
  notes: string | null
}

export function buildJournalInput(astronaut: Astronaut, day: number, existing: HealthJournal | null, values: JournalDraftValues, defaults: JournalDefaults = { timeUtc: NEW_ENTRY_TIME_UTC, sourceId: NEW_ENTRY_SOURCE_ID }): HealthJournalInput {
  return {
    timestamp: existing?.timestamp ?? `${missionDayIsoDate(astronaut.mission_start_date, day)}T${defaults.timeUtc}Z`,
    mission_day: day,
    sleep_hours_last_night: values.sleep,
    mood_score: values.mood,
    notes: values.notes,
    source_type: 'synthetic',
    source_id: existing?.source_id ?? defaults.sourceId,
  }
}
