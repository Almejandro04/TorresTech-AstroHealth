/**
 * Typed copy of docs/examples/mission_seed.json (contract v0.1.0).
 * `npm run check:mocks` verifies that it still matches the shared file.
 */
import type { Astronaut, HealthJournalInput, HealthReadingInput, MoodScore } from '../../types/health'

export const SEED_SOURCE_ID = 'SYN-CORE-001'

export type SeedReading = HealthReadingInput & { astronaut_id: string }
export type SeedJournal = HealthJournalInput & { astronaut_id: string }

export const seedAstronauts: Astronaut[] = [
  { astronaut_id: 'AST-001', name: 'Demo Astronaut 1', is_fictional: true, mission_start_date: '2026-11-01', planned_duration_days: 30 },
  { astronaut_id: 'AST-002', name: 'Demo Astronaut 2', is_fictional: true, mission_start_date: '2026-11-01', planned_duration_days: 30 },
]

const reading = (day: number, heart: number, spo2: number, respiratory: number | null): SeedReading => ({
  astronaut_id: 'AST-001',
  timestamp: `2026-11-0${day}T12:00:00Z`,
  mission_day: day,
  heart_rate_bpm: heart,
  spo2_percent: spo2,
  respiratory_rate_bpm: respiratory,
  measurement_context: 'rest',
  source_type: 'synthetic',
  source_id: SEED_SOURCE_ID,
})

const journal = (day: number, sleep: number, mood: MoodScore): SeedJournal => ({
  astronaut_id: 'AST-001',
  timestamp: `2026-11-0${day}T08:00:00Z`,
  mission_day: day,
  sleep_hours_last_night: sleep,
  mood_score: mood,
  notes: null,
  source_type: 'synthetic',
  source_id: SEED_SOURCE_ID,
})

export const seedReadings: SeedReading[] = [
  reading(1, 72, 98, 16),
  reading(2, 72, 98, 16),
  reading(3, 72, 98, 16),
  reading(4, 72, 98, 16),
  reading(5, 72, 98, 16),
  reading(6, 78, 97, 16),
  reading(7, 84, 97, null),
]

export const seedJournal: SeedJournal[] = [
  journal(1, 7.5, 4),
  journal(2, 7.5, 4),
  journal(3, 7.5, 4),
  journal(4, 7.5, 4),
  journal(5, 7.5, 4),
  journal(6, 6.5, 3),
  journal(7, 5.5, 2),
]
