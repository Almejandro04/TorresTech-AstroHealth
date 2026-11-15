import { useEffect, useRef } from 'react'
import { ArrowLeft, ArrowRight, FlaskConical, Lock } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { MetricChart } from '../components/MetricChart'
import { AlertStatusBadge, Callout, ErrorState, LoadingBlock, PageHeader, RefreshDataButton, Segmented, SeverityBadge } from '../components/ui'
import { useMission } from '../hooks/MissionContext'
import { useHistory } from '../hooks/useHistory'
import { METRICS, describeValue, formatDelta, hasBaseline } from '../lib/metrics'
import { buildMetricHistory } from '../lib/series'
import { formatObservation, formatUtcDateTime, missionDayOf } from '../lib/time'
import type { Astronaut, HealthAlert } from '../types/health'

type StatusFilter = 'all' | 'active' | 'resolved'
const isFilter = (value: string | null): value is StatusFilter => value === 'active' || value === 'resolved'

function AlertDetail({ alert, astronaut }: { alert: HealthAlert; astronaut: Astronaut }) {
  const { view, linkTo } = useMission()
  const info = METRICS[alert.indicator]
  const range = { fromDay: Math.max(1, alert.mission_day - 6), toDay: alert.mission_day }
  const history = useHistory(range)
  const baseline = view.status === 'ready' && hasBaseline(alert.indicator) ? view.data.data.baselines[alert.indicator] : null
  const delta = alert.baseline_value === null ? null : alert.observed_value - alert.baseline_value
  const windowStartDay = missionDayOf(astronaut.mission_start_date, alert.window_start)
  const windowEndDay = missionDayOf(astronaut.mission_start_date, alert.window_end)

  return (
    <article className="alert-detail" aria-labelledby="alert-detail-title">
      <div className="alert-detail__badges">
        <SeverityBadge severity={alert.severity} />
        <AlertStatusBadge status={alert.status} />
      </div>
      <h2 id="alert-detail-title" tabIndex={-1}>{alert.description}</h2>
      <p className="alert-detail__meta mono">{info.label} · detected {formatObservation(alert.mission_day, alert.timestamp)}</p>

      <h3>What was observed</h3>
      <p className="alert-detail__explanation">{alert.explanation}</p>

      <h3>Evidence</h3>
      <dl className="facts facts--grid">
        <div><dt>Observed value</dt><dd><strong>{describeValue(alert.indicator, alert.observed_value)}</strong></dd></div>
        <div>
          <dt>Reference value</dt>
          <dd>{alert.baseline_value === null ? 'No reference applies to this alert' : describeValue(alert.indicator, alert.baseline_value)}</dd>
        </div>
        {delta !== null && <div><dt>Difference</dt><dd>{formatDelta(delta)} {alert.unit === 'score' ? 'points' : alert.unit === '%' ? 'percentage points' : alert.unit}</dd></div>}
        <div>
          <dt>Evidence window</dt>
          <dd className="mono">
            {alert.window_start === alert.window_end
              ? formatObservation(windowStartDay, alert.window_start)
              : `${formatObservation(windowStartDay, alert.window_start)} → ${formatObservation(windowEndDay, alert.window_end)}`}
          </dd>
        </div>
      </dl>

      {history.status === 'loading' && <LoadingBlock label="Loading the evidence chart…" rows={2} />}
      {history.status === 'error' && <ErrorState error={history.error} subject="the evidence chart" onRetry={history.retry} />}
      {history.status === 'ready' && (
        <figure className="alert-detail__chart">
          <figcaption>{info.label}, Day {range.fromDay} to Day {range.toDay} ({info.unit === 'of 5' ? 'score 1–5' : info.unit})</figcaption>
          <MetricChart
            history={buildMetricHistory(alert.indicator, history.data.readings, history.data.journal, range)}
            range={range}
            missionStartDate={astronaut.mission_start_date}
            baseline={baseline}
            highlight={{ start: alert.window_start, end: alert.window_end, label: 'Evidence window of this alert' }}
            height={190}
          />
        </figure>
      )}

      <h3>Status</h3>
      <p className="alert-detail__status">
        <Lock size={16} aria-hidden="true" />
        <span>
          {alert.status === 'resolved' && alert.resolved_at
            ? `Resolved by the analysis engine on ${formatObservation(missionDayOf(astronaut.mission_start_date, alert.resolved_at), alert.resolved_at)}.`
            : 'Active since it was detected.'}{' '}
          The analysis engine sets and clears this status; it cannot be changed here.
        </span>
      </p>

      <h3>Rule and provenance</h3>
      <dl className="facts facts--grid">
        <div><dt>Rule</dt><dd className="mono">{alert.rule_id} · version {alert.rule_version}</dd></div>
        <div><dt>Source</dt><dd className="mono"><FlaskConical size={12} aria-hidden="true" /> Synthetic · {alert.source_id}</dd></div>
        <div><dt>Alert ID</dt><dd className="mono">{alert.alert_id}</dd></div>
      </dl>
      <p className="alert-detail__disclaimer">
        Experimental rule output on synthetic data. It describes a pattern in the observations; it is not a diagnosis or treatment advice.
      </p>
      <Link className="link-arrow" to={linkTo('/analytics', { focus: alert.indicator })}>
        Open {info.label} in Analytics <ArrowRight size={14} aria-hidden="true" />
      </Link>
    </article>
  )
}

export function AlertsPage() {
  const { astronaut, alerts, view, unknownAstronautId, linkTo, source } = useMission()
  const { alertId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const filter: StatusFilter = isFilter(searchParams.get('status')) ? (searchParams.get('status') as StatusFilter) : 'all'
  const previousId = useRef(alertId)

  const all = alerts.status === 'ready' ? alerts.data.data : []
  const evaluation = alerts.status === 'ready' ? alerts.data.meta.evaluation_status : null
  const counts = { all: all.length, active: all.filter((a) => a.status === 'active').length, resolved: all.filter((a) => a.status === 'resolved').length }
  const visible = filter === 'all' ? all : all.filter((alert) => alert.status === filter)
  const requested = alertId ? all.find((alert) => alert.alert_id === alertId) : undefined
  const selected = requested ?? (alertId ? undefined : visible[0])

  // Opening an alert moves focus to its heading, so its explanation is read next.
  useEffect(() => {
    if (alertId && alertId !== previousId.current) document.getElementById('alert-detail-title')?.focus({ preventScroll: true })
    previousId.current = alertId
  }, [alertId, selected?.alert_id])

  const withFilter = (target: { pathname: string; search: string }) =>
    filter === 'all' ? target : { ...target, search: `${target.search}${target.search ? '&' : '?'}status=${filter}` }

  return (
    <>
      <PageHeader title="Alerts" lead="Experimental attention levels with their explanation and evidence. Read-only: you consult them, the analysis engine maintains them." actions={<RefreshDataButton />} />

      {unknownAstronautId && <Callout tone="warning" title="Astronaut profile not found"><p>Choose a profile in the mission bar.</p></Callout>}
      {view.status === 'error' && <ErrorState error={view.error} subject="the mission summary" onRetry={view.retry} />}
      {alerts.status === 'error' && <ErrorState error={alerts.error} subject="the alerts" onRetry={alerts.retry} />}
      {(alerts.status === 'loading' || (alerts.status === 'idle' && view.status === 'loading')) && <LoadingBlock label="Loading alerts…" />}

      {alerts.status === 'ready' && astronaut && (
        <div className={alerts.refreshing ? 'is-refreshing' : undefined}>
          {evaluation === 'not_implemented' && (
            <Callout tone="neutral" title="Analysis not available">
              <p>The alert analysis is not implemented in this data source, so nothing was evaluated. An empty list here is not an all-clear.</p>
            </Callout>
          )}
          {evaluation === 'insufficient_data' && (
            <Callout tone="neutral" title="More observations needed">
              <p>Alerts are evaluated once there are enough observations for a reference. Nothing was evaluated yet, which is not an all-clear.</p>
            </Callout>
          )}
          {evaluation === 'available' && all.length === 0 && (
            <Callout tone="info" title="No active alerts detected in the evaluated data">
              <p>
                The analysis ran on the observations available{alerts.data.meta.as_of ? ` as of ${formatUtcDateTime(alerts.data.meta.as_of)}` : ''}.
                This describes those observations only; it is not a statement about health.
              </p>
            </Callout>
          )}

          {evaluation === 'available' && all.length > 0 && (
            <>
              <div className="filters">
                <Segmented
                  legend="Status"
                  name="alert-status"
                  value={filter}
                  onChange={(value) => {
                    const next = new URLSearchParams(searchParams)
                    if (value === 'all') next.delete('status')
                    else next.set('status', value)
                    setSearchParams(next, { replace: true })
                  }}
                  options={[
                    { value: 'all', label: 'All', detail: String(counts.all) },
                    { value: 'active', label: 'Active', detail: String(counts.active) },
                    { value: 'resolved', label: 'Resolved', detail: String(counts.resolved) },
                  ]}
                />
                <p className="filters__summary" role="status">
                  <strong>{counts.active} active · {counts.resolved} resolved</strong>
                  {alerts.data.meta.as_of && <span className="mono">Evaluated as of {formatUtcDateTime(alerts.data.meta.as_of)}</span>}
                </p>
              </div>
              {source.kind === 'mock' && all.some((alert) => alert.rule_id === 'PRESENTATION-SAMPLE') && (
                <Callout tone="info" title="Presentation samples are shown" compact>
                  <p>Items marked “Presentation sample” illustrate other levels and statuses. No detection rule produced them.</p>
                </Callout>
              )}

              <div className={`master-detail${alertId ? ' has-selection' : ''}`}>
                <div className="master-detail__list">
                  <h2 className="visually-hidden">Alert list</h2>
                  {visible.length === 0 ? (
                    <p className="readout__muted">No {filter} alerts in this view.</p>
                  ) : (
                    <ul className="alert-list">
                      {visible.map((alert) => (
                        <li key={alert.alert_id}>
                          <Link
                            to={withFilter(linkTo(`/alerts/${alert.alert_id}`))}
                            className={`alert-list__item${selected?.alert_id === alert.alert_id ? ' is-selected' : ''}`}
                            aria-current={selected?.alert_id === alert.alert_id ? 'true' : undefined}
                          >
                            <span className="alert-list__badges"><SeverityBadge severity={alert.severity} /><AlertStatusBadge status={alert.status} /></span>
                            <span className="alert-list__title">{alert.description}</span>
                            <span className="alert-list__meta mono">{METRICS[alert.indicator].label} · {formatObservation(alert.mission_day, alert.timestamp)}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="master-detail__detail">
                  {alertId && (
                    <Link className="link-arrow master-detail__back" to={withFilter(linkTo('/alerts'))}>
                      <ArrowLeft size={14} aria-hidden="true" /> All alerts
                    </Link>
                  )}
                  {selected ? (
                    <AlertDetail key={selected.alert_id} alert={selected} astronaut={astronaut} />
                  ) : alertId ? (
                    <Callout tone="neutral" title="This alert is not in the current view">
                      <p>
                        <span className="mono">{alertId}</span> does not exist for this astronaut, or it was detected after the selected mission day.
                      </p>
                    </Callout>
                  ) : (
                    <p className="readout__muted">Select an alert to read its explanation and evidence.</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}
