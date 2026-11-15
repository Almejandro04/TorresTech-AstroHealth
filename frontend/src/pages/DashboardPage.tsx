import { ArrowDown, ArrowRight, ArrowUp, CircleDashed, FlaskConical, History, Minus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Sparkline } from '../components/Sparkline'
import { AlertStatusBadge, Callout, ErrorState, LoadingBlock, PageHeader, Section, SeverityBadge, Tag } from '../components/ui'
import { useMission } from '../hooks/MissionContext'
import { useHistory } from '../hooks/useHistory'
import type { MissionHistory } from '../hooks/useHistory'
import { CONTEXT_LABELS, METRICS, METRIC_ORDER, describeValue, formatDelta, formatNumber, hasBaseline, moodLabel } from '../lib/metrics'
import { buildMetricHistory } from '../lib/series'
import type { DayRange } from '../lib/series'
import { formatObservation, formatUtcDateTime, missionDayStartMs } from '../lib/time'
import type { Astronaut, BaselineMetric, HealthSummary, MetricName, MetricSnapshot } from '../types/health'

const TREND_DAYS = 7

function ReferenceCell({ metric, snapshot, baseline }: { metric: MetricName; snapshot: MetricSnapshot; baseline: BaselineMetric | null }) {
  const unit = METRICS[metric].unit
  if (!baseline) {
    return <p className="readout__muted">No reference. Mood is an ordinal self-report, shown directly.</p>
  }
  if (baseline.status === 'not_implemented') {
    return <p className="readout__muted"><CircleDashed size={14} aria-hidden="true" /> Reference not available. Analysis is not implemented.</p>
  }
  if (baseline.status === 'insufficient_data' || baseline.value === null) {
    return <p className="readout__muted"><CircleDashed size={14} aria-hidden="true" /> More observations needed ({baseline.sample_count} so far).</p>
  }
  const comparable = snapshot.value !== null && snapshot.measurement_context === baseline.measurement_context
  const delta = comparable && snapshot.value !== null ? Math.round((snapshot.value - baseline.value) * 10) / 10 : null
  const DeltaIcon = delta === null || delta === 0 ? Minus : delta > 0 ? ArrowUp : ArrowDown
  return (
    <>
      <p className="readout__reference">
        <strong>{formatNumber(baseline.value)}</strong> {unit}
      </p>
      <p className="readout__muted">
        {baseline.measurement_context ? `${CONTEXT_LABELS[baseline.measurement_context]} · ` : ''}{baseline.sample_count} observations
      </p>
      {delta !== null ? (
        <p className="readout__delta">
          <DeltaIcon size={14} aria-hidden="true" />
          {delta === 0
            ? 'Same as reference'
            : `${formatDelta(delta)} ${metric === 'spo2_percent' ? 'percentage points' : unit} vs reference`}
        </p>
      ) : snapshot.value !== null ? (
        <p className="readout__muted">Not compared: the latest value has a different measurement context.</p>
      ) : null}
    </>
  )
}

interface ReadoutRowProps {
  metric: MetricName
  summary: HealthSummary
  astronaut: Astronaut
  history: MissionHistory | null
  range: DayRange | null
  analyticsLink: { pathname: string; search: string }
}

/** One indicator with everything that qualifies it kept together: value, unit, its own time, context, source. */
function ReadoutRow({ metric, summary, astronaut, history, range, analyticsLink }: ReadoutRowProps) {
  const info = METRICS[metric]
  const snapshot = summary.latest_metrics[metric]
  const baseline = hasBaseline(metric) ? summary.baselines[metric] : null
  const Icon = info.icon
  const olderDay = snapshot.mission_day !== null && summary.mission_day !== null && snapshot.mission_day < summary.mission_day
  const metricHistory = history && range ? buildMetricHistory(metric, history.readings, history.journal, range) : null
  const seriesKey = info.source === 'journal' ? 'journal' : snapshot.measurement_context
  const series = metricHistory?.series.find((candidate) => candidate.key === seriesKey)

  return (
    <li className="readout__row">
      <div className="readout__cell readout__indicator">
        <Icon size={20} aria-hidden="true" />
        <div>
          <h3>{info.label}</h3>
          <p className="readout__muted">
            {info.sourceLabel}
            {snapshot.measurement_context ? ` · ${CONTEXT_LABELS[snapshot.measurement_context]}` : ''}
          </p>
        </div>
      </div>

      <div className="readout__cell readout__value">
        <span className="readout__label">Latest value</span>
        {snapshot.value === null ? (
          <p className="readout__missing"><CircleDashed size={16} aria-hidden="true" /> Not recorded <span className="readout__unit">{info.unit === 'of 5' ? 'score 1–5' : info.unit}</span></p>
        ) : (
          <p>
            <span className="readout__number">{formatNumber(snapshot.value)}</span>
            <span className="readout__unit">{info.unit}</span>
            {metric === 'mood_score' && <span className="readout__qualifier">{moodLabel(snapshot.value)}</span>}
          </p>
        )}
      </div>

      <div className="readout__cell">
        <span className="readout__label">Observed</span>
        {snapshot.timestamp !== null && snapshot.mission_day !== null ? (
          <>
            <p className="mono">{formatObservation(snapshot.mission_day, snapshot.timestamp)}</p>
            {olderDay && (
              <p className="readout__older">
                <Tag icon={History}>Earlier day</Tag>
                <span>No value on Day {summary.mission_day}; this is the most recent one.</span>
              </p>
            )}
            <p className="readout__source mono"><FlaskConical size={12} aria-hidden="true" /> Synthetic · {snapshot.source_id} · {snapshot.record_id}</p>
          </>
        ) : (
          <p className="readout__muted">No observation yet</p>
        )}
      </div>

      <div className="readout__cell">
        <span className="readout__label">Reference</span>
        <ReferenceCell metric={metric} snapshot={snapshot} baseline={baseline} />
      </div>

      <div className="readout__cell readout__trend">
        <span className="readout__label">Last {TREND_DAYS} days</span>
        {metricHistory && range && series ? (
          <>
            <Sparkline series={series} emptyRecords={metricHistory.emptyRecords} range={range} missionStartMs={missionDayStartMs(astronaut.mission_start_date, 1)} />
            <span className="visually-hidden">
              Days {range.fromDay} to {range.toDay}: {series.points.map((point) => `Day ${point.day}, ${describeValue(metric, point.value)}`).join('; ')}.
            </span>
          </>
        ) : (
          <p className="readout__muted">{history ? 'No history' : '…'}</p>
        )}
        <Link className="link-arrow" to={{ ...analyticsLink, search: `${analyticsLink.search}${analyticsLink.search ? '&' : '?'}focus=${metric}` }} aria-label={`Open ${info.label} in Analytics`}>
          Chart <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>
    </li>
  )
}

function AttentionSummary({ summary }: { summary: HealthSummary }) {
  const { linkTo } = useMission()
  const { evaluation_status: status, active_count: count, highest_severity: highest, recent } = summary.alert_summary

  if (status === 'not_implemented') {
    return <Callout tone="neutral" title="Analysis not available">The alert analysis is not implemented in this data source. This is not an all-clear.</Callout>
  }
  if (status === 'insufficient_data') {
    return <Callout tone="neutral" title="More observations needed">Alerts are evaluated once there are enough observations for a reference. This is not an all-clear.</Callout>
  }
  if (!count) {
    return <Callout tone="info" title="No active alerts detected in the evaluated data">This describes the evaluated observations only. It is not a statement about health.</Callout>
  }
  return (
    <>
      <p className="attention__count">
        <strong>{count}</strong> active {count === 1 ? 'alert' : 'alerts'}
        {highest && <> · highest level <SeverityBadge severity={highest} /></>}
      </p>
      <ul className="link-list">
        {recent.map((alert) => (
          <li key={alert.alert_id}>
            <Link to={linkTo(`/alerts/${alert.alert_id}`)} className="link-list__item">
              <span className="link-list__badges"><SeverityBadge severity={alert.severity} /><AlertStatusBadge status={alert.status} /></span>
              <span className="link-list__title">{alert.description}</span>
              <span className="link-list__meta mono">{METRICS[alert.indicator].label} · {formatObservation(alert.mission_day, alert.timestamp)}</span>
              <ArrowRight className="link-list__arrow" size={16} aria-hidden="true" />
            </Link>
          </li>
        ))}
      </ul>
      {count > recent.length && <p className="readout__muted">Showing the {recent.length} most recent.</p>}
    </>
  )
}

function JournalSummary({ summary }: { summary: HealthSummary }) {
  const { linkTo, viewDay } = useMission()
  const entry = summary.latest_journal
  const targetDay = viewDay ?? 1
  const hasEntryForViewDay = entry !== null && entry.mission_day === viewDay
  return (
    <>
      {entry ? (
        <dl className="facts">
          <div><dt>Latest entry</dt><dd className="mono">{formatObservation(entry.mission_day, entry.timestamp)}</dd></div>
          <div><dt>Sleep last night</dt><dd>{entry.sleep_hours_last_night === null ? 'Not recorded' : describeValue('sleep_hours_last_night', entry.sleep_hours_last_night)}</dd></div>
          <div><dt>Mood</dt><dd>{entry.mood_score === null ? 'Not recorded' : describeValue('mood_score', entry.mood_score)}</dd></div>
          <div><dt>Notes</dt><dd className="facts__notes">{entry.notes ?? 'No notes'}</dd></div>
        </dl>
      ) : (
        <p className="readout__muted">No journal entry recorded yet.</p>
      )}
      {entry && !hasEntryForViewDay && viewDay !== null && <p className="readout__muted">No entry for Day {viewDay} yet.</p>}
      <Link className="button button--secondary" to={linkTo('/journal', { entry: String(targetDay) })}>
        {hasEntryForViewDay ? `Review Day ${targetDay} entry` : `Add Day ${targetDay} entry`} <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </>
  )
}

export function DashboardPage() {
  const { astronaut, view, viewDay, unknownAstronautId, profiles, linkTo } = useMission()
  const range: DayRange | null = viewDay === null ? null : { fromDay: Math.max(1, viewDay - TREND_DAYS + 1), toDay: viewDay }
  const history = useHistory(range)
  const summary = view.status === 'ready' ? view.data.data : null
  const meta = view.status === 'ready' ? view.data.meta : null
  const refreshing = view.status === 'ready' && view.refreshing

  return (
    <>
      <PageHeader title="Dashboard" lead="Latest recorded value of each indicator, with the moment it was observed." />

      {profiles.status === 'error' && <ErrorState error={profiles.error} subject="the mission profiles" onRetry={profiles.retry} />}
      {unknownAstronautId && (
        <Callout tone="warning" title="Astronaut profile not found">
          <p>No fictional profile has the ID <span className="mono">{unknownAstronautId}</span>. Choose a profile in the mission bar. This is different from a profile with no observations.</p>
        </Callout>
      )}
      {view.status === 'error' && <ErrorState error={view.error} subject="the mission summary" onRetry={view.retry} />}
      {(profiles.status === 'loading' || view.status === 'loading') && <LoadingBlock label="Loading latest observations…" rows={5} />}

      {summary && astronaut && (
        <>
          {summary.mission_day === null && (
            <Callout tone="neutral" title={`No observations recorded for ${astronaut.name} yet`}>
              <p>Indicators appear here once readings or journal entries exist. Empty values below mean “not recorded”, never zero.</p>
            </Callout>
          )}

          <Section title="Latest observations" note="Each value keeps its own observation time" busy={refreshing}>
            <div className="readout">
              <div className="readout__head" aria-hidden="true">
                <span>Indicator</span><span>Latest value</span><span>Observed</span><span>Reference</span><span>Last {TREND_DAYS} days</span>
              </div>
              <ul className="readout__rows">
                {METRIC_ORDER.map((metric) => (
                  <ReadoutRow
                    key={metric}
                    metric={metric}
                    summary={summary}
                    astronaut={astronaut}
                    history={history.status === 'ready' ? history.data : null}
                    range={range}
                    analyticsLink={linkTo('/analytics')}
                  />
                ))}
              </ul>
            </div>
            {history.status === 'error' && <ErrorState error={history.error} subject="the recent history" onRetry={history.retry} />}
          </Section>

          <div className="split">
            <Section
              title="Attention"
              note="Experimental, consultative"
              busy={refreshing}
              actions={<Link className="link-arrow" to={linkTo('/alerts')}>All alerts <ArrowRight size={14} aria-hidden="true" /></Link>}
            >
              <AttentionSummary summary={summary} />
            </Section>
            <Section title="Daily journal" note="Self-report" busy={refreshing}>
              <JournalSummary summary={summary} />
            </Section>
          </div>

          {meta?.as_of && (
            <p className="page-foot mono">Summary as of {formatUtcDateTime(meta.as_of)} · schema {meta.schema_version}</p>
          )}
        </>
      )}
    </>
  )
}
