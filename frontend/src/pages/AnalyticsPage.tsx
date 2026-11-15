import { useEffect, useId } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MetricChart, describeBaseline } from '../components/MetricChart'
import { Callout, ErrorState, LoadingBlock, PageHeader, Section, Segmented } from '../components/ui'
import { useMission } from '../hooks/MissionContext'
import { useHistory } from '../hooks/useHistory'
import type { MissionHistory } from '../hooks/useHistory'
import { METRICS, hasBaseline } from '../lib/metrics'
import { buildMetricHistory } from '../lib/series'
import type { DayRange } from '../lib/series'
import { formatUtcDate, missionDayStartMs } from '../lib/time'
import type { Astronaut, HealthSummary, MetricName } from '../types/health'

type Preset = '3d' | '7d' | 'all' | 'custom'
const PRESETS: { value: Preset; label: string }[] = [
  { value: '3d', label: '3 days' },
  { value: '7d', label: '7 days' },
  { value: 'all', label: 'Mission to date' },
  { value: 'custom', label: 'Custom' },
]
const isPreset = (value: string | null): value is Preset => PRESETS.some((preset) => preset.value === value)
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

function resolveRange(preset: Preset, viewDay: number, from: string | null, to: string | null): DayRange {
  if (preset === '3d') return { fromDay: Math.max(1, viewDay - 2), toDay: viewDay }
  if (preset === 'all') return { fromDay: 1, toDay: viewDay }
  if (preset === 'custom') {
    const toDay = clamp(Number(to) || viewDay, 1, viewDay)
    return { fromDay: clamp(Number(from) || 1, 1, toDay), toDay }
  }
  return { fromDay: Math.max(1, viewDay - 6), toDay: viewDay }
}

interface ChartBlockProps {
  metric: MetricName
  history: MissionHistory
  range: DayRange
  astronaut: Astronaut
  summary: HealthSummary
}

function ChartBlock({ metric, history, range, astronaut, summary }: ChartBlockProps) {
  const info = METRICS[metric]
  const baseline = hasBaseline(metric) ? summary.baselines[metric] : null
  const metricHistory = buildMetricHistory(metric, history.readings, history.journal, range)
  return (
    <article className="chart-block" id={`chart-${metric}`} tabIndex={-1} aria-labelledby={`chart-${metric}-title`}>
      <header className="chart-block__head">
        <h3 id={`chart-${metric}-title`}>{info.label}</h3>
        <p className="mono">{metric === 'mood_score' ? 'score 1–5' : info.unit} · {metricHistory.observationCount} {metricHistory.observationCount === 1 ? 'value' : 'values'}</p>
      </header>
      <MetricChart history={metricHistory} range={range} missionStartDate={astronaut.mission_start_date} baseline={baseline} />
      <p className="chart-block__reference">{describeBaseline(info.label, info.unit, baseline)}</p>
    </article>
  )
}

export function AnalyticsPage() {
  const { astronaut, view, viewDay, isHistorical, unknownAstronautId } = useMission()
  const [searchParams, setSearchParams] = useSearchParams()
  const fromId = useId()
  const toId = useId()

  const preset: Preset = isPreset(searchParams.get('range')) ? (searchParams.get('range') as Preset) : '7d'
  const range = viewDay === null ? null : resolveRange(preset, viewDay, searchParams.get('from'), searchParams.get('to'))
  const history = useHistory(range)
  const summary = view.status === 'ready' ? view.data.data : null
  const focus = searchParams.get('focus')

  // Arriving from a Dashboard row: bring that chart into view once it exists.
  const historyReady = history.status === 'ready'
  useEffect(() => {
    if (!focus || !historyReady) return
    const target = document.getElementById(`chart-${focus}`)
    target?.scrollIntoView({ block: 'center' })
    target?.focus({ preventScroll: true })
  }, [focus, historyReady])

  const update = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    next.delete('focus')
    for (const [key, value] of Object.entries(patch)) {
      if (value === null) next.delete(key)
      else next.set(key, value)
    }
    setSearchParams(next, { replace: true })
  }

  const selectPreset = (value: Preset) => {
    if (value === 'custom' && range) update({ range: 'custom', from: String(range.fromDay), to: String(range.toDay) })
    else update({ range: value === '7d' ? null : value, from: null, to: null })
  }

  const days = viewDay === null ? [] : Array.from({ length: viewDay }, (_, index) => index + 1)
  const dateOf = (day: number) => (astronaut ? formatUtcDate(missionDayStartMs(astronaut.mission_start_date, day)) : '')

  return (
    <>
      <PageHeader title="Analytics" lead="Recorded values over time, compared with the individual reference when one exists." />

      {unknownAstronautId && <Callout tone="warning" title="Astronaut profile not found"><p>Choose a profile in the mission bar.</p></Callout>}
      {view.status === 'error' && <ErrorState error={view.error} subject="the mission summary" onRetry={view.retry} />}
      {view.status === 'loading' && <LoadingBlock label="Loading mission view…" />}

      {summary && astronaut && viewDay === null && (
        <Callout tone="neutral" title="No observations to chart yet">
          <p>{astronaut.name} has no readings or journal entries. Charts appear once observations exist.</p>
        </Callout>
      )}

      {summary && astronaut && range && viewDay !== null && (
        <>
          <div className="filters">
            <Segmented legend="Period" name="period" value={preset} options={PRESETS} onChange={selectPreset} />
            {preset === 'custom' && (
              <div className="filters__custom">
                <div className="field field--inline">
                  <label className="field__label" htmlFor={fromId}>From day</label>
                  <select id={fromId} className="select" value={range.fromDay} onChange={(event) => update({ from: event.target.value })}>
                    {days.filter((day) => day <= range.toDay).map((day) => <option key={day} value={day}>Day {day}</option>)}
                  </select>
                </div>
                <div className="field field--inline">
                  <label className="field__label" htmlFor={toId}>To day</label>
                  <select id={toId} className="select" value={range.toDay} onChange={(event) => update({ to: event.target.value })}>
                    {days.filter((day) => day >= range.fromDay).map((day) => <option key={day} value={day}>Day {day}</option>)}
                  </select>
                </div>
              </div>
            )}
            <p className="filters__summary" role="status">
              <strong>Day {range.fromDay}{range.toDay !== range.fromDay ? ` to Day ${range.toDay}` : ''}</strong>
              <span className="mono">{dateOf(range.fromDay)}{range.toDay !== range.fromDay ? ` to ${dateOf(range.toDay)}` : ''} (UTC)</span>
              {isHistorical && <span>Limited to the historical view, Day {viewDay}.</span>}
            </p>
          </div>

          {history.status === 'loading' && <LoadingBlock label="Loading history…" rows={4} />}
          {history.status === 'error' && <ErrorState error={history.error} subject="the history for this period" onRetry={history.retry} />}
          {history.status === 'ready' && (
            <>
              <Section title="Vital readings" note="Point-in-time measurements" busy={history.refreshing}>
                <div className="chart-grid">
                  {(['heart_rate_bpm', 'spo2_percent', 'respiratory_rate_bpm'] as const).map((metric) => (
                    <ChartBlock key={metric} metric={metric} history={history.data} range={range} astronaut={astronaut} summary={summary} />
                  ))}
                </div>
              </Section>
              <Section title="Daily journal" note="One self-report per mission day" busy={history.refreshing}>
                <div className="chart-grid chart-grid--two">
                  {(['sleep_hours_last_night', 'mood_score'] as const).map((metric) => (
                    <ChartBlock key={metric} metric={metric} history={history.data} range={range} astronaut={astronaut} summary={summary} />
                  ))}
                </div>
              </Section>
            </>
          )}
        </>
      )}
    </>
  )
}
