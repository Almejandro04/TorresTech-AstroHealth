import type { HealthAlert } from '../../types/health'
import { SEED_SOURCE_ID } from './seed'

/** Copied verbatim from docs/examples/api_examples.json, case `explainable_synthetic_alert`. */
export const contractAlert: HealthAlert = {
  alert_id: 'ALERT-0001',
  astronaut_id: 'AST-001',
  timestamp: '2026-11-07T12:00:00Z',
  mission_day: 7,
  indicator: 'heart_rate_bpm',
  severity: 'warning',
  status: 'active',
  description: 'Introduced synthetic resting heart-rate change.',
  explanation:
    'Fixture days 6-7 have a resting mean of 81 beats/min; the synthetic days 1-5 reference mean is 72. This controlled example illustrates explanation fields, not a validated medical threshold.',
  rule_id: 'DEMO-HR-CHANGE',
  rule_version: 'fixture-1',
  observed_value: 81,
  baseline_value: 72,
  unit: 'beats/min',
  window_start: '2026-11-06T12:00:00Z',
  window_end: '2026-11-07T12:00:00Z',
  resolved_at: null,
  source_type: 'synthetic',
  source_id: SEED_SOURCE_ID,
}

export const PRESENTATION_RULE_ID = 'PRESENTATION-SAMPLE'

const SAMPLE_NOTE =
  'Presentation sample added by the frontend mock to review this attention level. No detection rule produced it and the level shown has no medical meaning.'

/**
 * Presentation-only samples. The shared fixtures contain a single warning, so these let a
 * reviewer see the other levels and the resolved status. Every number is copied from the seed
 * readings or the fixture reference; nothing here is new evidence, and each explanation says so.
 */
export const presentationAlerts: HealthAlert[] = [
  {
    alert_id: 'SAMPLE-CRITICAL-HR',
    astronaut_id: 'AST-001',
    timestamp: '2026-11-07T12:00:00Z',
    mission_day: 7,
    indicator: 'heart_rate_bpm',
    severity: 'critical',
    status: 'active',
    description: 'Presentation sample: highest attention level on the day-7 resting reading.',
    explanation: `The day-7 resting reading is 84 beats/min; the synthetic days 1-5 reference mean is 72. ${SAMPLE_NOTE}`,
    rule_id: PRESENTATION_RULE_ID,
    rule_version: 'frontend-mock-1',
    observed_value: 84,
    baseline_value: 72,
    unit: 'beats/min',
    window_start: '2026-11-07T12:00:00Z',
    window_end: '2026-11-07T12:00:00Z',
    resolved_at: null,
    source_type: 'synthetic',
    source_id: SEED_SOURCE_ID,
  },
  {
    alert_id: 'SAMPLE-INFO-RR',
    astronaut_id: 'AST-001',
    timestamp: '2026-11-07T12:00:00Z',
    mission_day: 7,
    indicator: 'respiratory_rate_bpm',
    severity: 'info',
    status: 'active',
    description: 'Presentation sample: the latest respiratory-rate value comes from an earlier reading.',
    explanation: `The day-7 reading has no respiratory-rate value, so the latest recorded value is 16 breaths/min from day 6. No reference comparison applies to this sample. ${SAMPLE_NOTE}`,
    rule_id: PRESENTATION_RULE_ID,
    rule_version: 'frontend-mock-1',
    observed_value: 16,
    baseline_value: null,
    unit: 'breaths/min',
    window_start: '2026-11-06T12:00:00Z',
    window_end: '2026-11-07T12:00:00Z',
    resolved_at: null,
    source_type: 'synthetic',
    source_id: SEED_SOURCE_ID,
  },
  {
    alert_id: 'SAMPLE-INFO-SPO2',
    astronaut_id: 'AST-001',
    timestamp: '2026-11-06T12:00:00Z',
    mission_day: 6,
    indicator: 'spo2_percent',
    severity: 'info',
    status: 'resolved',
    description: 'Presentation sample: day-over-day change in blood oxygen on day 6.',
    explanation: `The day-6 resting reading is 97%, one point below day 5 and the synthetic days 1-5 reference mean of 98. The day-7 reading repeats 97%, with no further day-over-day change, so this sample is shown as resolved. ${SAMPLE_NOTE}`,
    rule_id: PRESENTATION_RULE_ID,
    rule_version: 'frontend-mock-1',
    observed_value: 97,
    baseline_value: 98,
    unit: '%',
    window_start: '2026-11-05T12:00:00Z',
    window_end: '2026-11-06T12:00:00Z',
    resolved_at: '2026-11-07T12:00:00Z',
    source_type: 'synthetic',
    source_id: SEED_SOURCE_ID,
  },
]
