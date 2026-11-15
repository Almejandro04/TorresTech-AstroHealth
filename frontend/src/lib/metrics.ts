import { BedDouble, Droplets, HeartPulse, Smile, Wind } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { BaselineMetricName, MeasurementContext, MetricName, MoodScore, Severity } from '../types/health'

export interface MetricInfo {
  name: MetricName
  label: string
  /** Unit as displayed. Mood is an ordinal 1-5 self-report, shown with its label. */
  unit: string
  source: 'reading' | 'journal'
  sourceLabel: string
  icon: LucideIcon
}

export const METRIC_ORDER: MetricName[] = [
  'heart_rate_bpm',
  'spo2_percent',
  'respiratory_rate_bpm',
  'sleep_hours_last_night',
  'mood_score',
]

export const METRICS: Record<MetricName, MetricInfo> = {
  heart_rate_bpm: { name: 'heart_rate_bpm', label: 'Heart rate', unit: 'beats/min', source: 'reading', sourceLabel: 'Vital reading', icon: HeartPulse },
  spo2_percent: { name: 'spo2_percent', label: 'Blood oxygen (SpO₂)', unit: '%', source: 'reading', sourceLabel: 'Vital reading', icon: Droplets },
  respiratory_rate_bpm: { name: 'respiratory_rate_bpm', label: 'Respiratory rate', unit: 'breaths/min', source: 'reading', sourceLabel: 'Vital reading', icon: Wind },
  sleep_hours_last_night: { name: 'sleep_hours_last_night', label: 'Sleep duration', unit: 'hours', source: 'journal', sourceLabel: 'Daily journal', icon: BedDouble },
  mood_score: { name: 'mood_score', label: 'Mood', unit: 'of 5', source: 'journal', sourceLabel: 'Daily journal', icon: Smile },
}

export const MOOD_LABELS: Record<MoodScore, string> = { 1: 'Very low', 2: 'Low', 3: 'Neutral', 4: 'High', 5: 'Very high' }
export const MOOD_SCORES: MoodScore[] = [1, 2, 3, 4, 5]

export const isMoodScore = (value: number): value is MoodScore => Number.isInteger(value) && value >= 1 && value <= 5
export const moodLabel = (value: number): string => (isMoodScore(value) ? MOOD_LABELS[value] : 'Unlabeled score')

export const CONTEXT_LABELS: Record<MeasurementContext, string> = {
  rest: 'Rest',
  exercise: 'Exercise',
  sleep: 'Sleep',
  unknown: 'Unknown context',
}

export const SEVERITY_LABELS: Record<Severity, string> = { info: 'Info', warning: 'Warning', critical: 'Critical' }

export const hasBaseline = (metric: MetricName): metric is BaselineMetricName => metric !== 'mood_score'

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })
export const formatNumber = (value: number): string => numberFormat.format(value)

/** "84 beats/min", "97%", "5.5 hours", "Low (2 of 5)" */
export function describeValue(metric: MetricName, value: number): string {
  if (metric === 'mood_score') return `${moodLabel(value)} (${formatNumber(value)} of 5)`
  if (metric === 'spo2_percent') return `${formatNumber(value)}%`
  return `${formatNumber(value)} ${METRICS[metric].unit}`
}

/** Signed arithmetic difference, e.g. "+12" or "−2". It states a difference, not a judgement. */
export function formatDelta(delta: number): string {
  const rounded = Math.round(delta * 10) / 10
  if (rounded === 0) return '0'
  return `${rounded > 0 ? '+' : '−'}${formatNumber(Math.abs(rounded))}`
}
