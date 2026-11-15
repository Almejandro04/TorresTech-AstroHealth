import { useId } from 'react'
import { ChevronLeft, ChevronRight, FlaskConical, History } from 'lucide-react'
import { useMission } from '../hooks/MissionContext'
import { formatUtcDate, formatUtcDateTime, formatUtcShortDate, missionDayStartMs } from '../lib/time'
import type { Astronaut } from '../types/health'

interface TimelineProps {
  astronaut: Astronaut
  viewDay: number | null
  latestDay: number | null
  alertDays: Set<number>
  onSelect: (day: number) => void
}

/**
 * The whole planned mission at a glance. Recorded days are pointer shortcuts to the same
 * choice the "Mission view" select offers; the select is the keyboard and screen-reader path,
 * so the strip itself is hidden from assistive technology instead of adding thirty stops.
 */
function MissionTimeline({ astronaut, viewDay, latestDay, alertDays, onSelect }: TimelineProps) {
  const days = Array.from({ length: astronaut.planned_duration_days }, (_, index) => index + 1)
  return (
    <div className="timeline" aria-hidden="true">
      {days.map((day) => {
        const state =
          viewDay !== null && day === viewDay ? 'current'
          : viewDay !== null && day < viewDay ? 'in-view'
          : latestDay !== null && day <= latestDay ? 'later'
          : 'planned'
        const title = `Day ${day} · ${formatUtcShortDate(missionDayStartMs(astronaut.mission_start_date, day))}`
        const marker = alertDays.has(day) ? <span className="timeline__alert" /> : null
        return latestDay !== null && day <= latestDay ? (
          <button key={day} type="button" tabIndex={-1} className={`timeline__day timeline__day--${state}`} title={title} onClick={() => onSelect(day)}>
            {marker}
          </button>
        ) : (
          <span key={day} className={`timeline__day timeline__day--${state}`} title={`${title} · planned`} />
        )
      })}
    </div>
  )
}

export function MissionBar({ onOpenDemo }: { onOpenDemo: () => void }) {
  const mission = useMission()
  const { profiles, astronaut, unknownAstronautId, view, latestDay, viewDay, isHistorical, alerts, source } = mission
  const astronautFieldId = useId()
  const dayFieldId = useId()

  const profileList = profiles.status === 'ready' ? profiles.data.data : []
  const asOf = view.status === 'ready' ? view.data.meta.as_of : null
  const alertDays = new Set(alerts.status === 'ready' ? alerts.data.data.map((alert) => alert.mission_day) : [])
  const dayOptions = latestDay === null ? [] : Array.from({ length: latestDay }, (_, index) => latestDay - index)
  const dayLabel = (day: number) =>
    astronaut ? `Day ${day} · ${formatUtcShortDate(missionDayStartMs(astronaut.mission_start_date, day))}${day === latestDay ? ' · latest' : ''}` : `Day ${day}`

  let caption = 'Loading mission view…'
  if (profiles.status === 'error' || view.status === 'error') caption = 'Mission view unavailable'
  else if (unknownAstronautId) caption = 'Unknown profile'
  else if (astronaut && view.status === 'ready') {
    caption = asOf
      ? `As of ${formatUtcDateTime(asOf)}`
      : `No observations yet · mission starts ${formatUtcDate(missionDayStartMs(astronaut.mission_start_date, 1))} (UTC)`
  }

  return (
    <div className="mission-bar">
      <div className="mission-bar__inner">
        <div className="mission-bar__field">
          <label className="eyebrow" htmlFor={astronautFieldId}>Astronaut · fictional profile</label>
          <select
            id={astronautFieldId}
            className="select"
            value={astronaut?.astronaut_id ?? ''}
            disabled={profileList.length === 0}
            onChange={(event) => mission.selectAstronaut(event.target.value)}
          >
            {!astronaut && <option value="">{profiles.status === 'loading' ? 'Loading profiles…' : unknownAstronautId ? `Unknown: ${unknownAstronautId}` : 'No profile'}</option>}
            {profileList.map((profile) => (
              <option key={profile.astronaut_id} value={profile.astronaut_id}>{profile.name} · {profile.astronaut_id}</option>
            ))}
          </select>
        </div>

        <div className="mission-bar__field">
          <label className="eyebrow" htmlFor={dayFieldId}>
            Mission view{astronaut ? ` · of ${astronaut.planned_duration_days} days` : ''}
          </label>
          <div className="stepper">
            <button
              type="button"
              className="icon-button stepper__step"
              aria-label="View previous mission day"
              disabled={viewDay === null || viewDay <= 1}
              onClick={() => viewDay !== null && mission.selectViewDay(viewDay - 1)}
            >
              <ChevronLeft size={18} aria-hidden="true" />
            </button>
            <select
              id={dayFieldId}
              className="select"
              value={viewDay ?? ''}
              disabled={dayOptions.length === 0}
              onChange={(event) => mission.selectViewDay(Number(event.target.value))}
            >
              {dayOptions.length === 0 && <option value="">{view.status === 'loading' ? 'Loading…' : 'No observations yet'}</option>}
              {dayOptions.map((day) => <option key={day} value={day}>{dayLabel(day)}</option>)}
            </select>
            <button
              type="button"
              className="icon-button stepper__step"
              aria-label="View next mission day"
              disabled={viewDay === null || latestDay === null || viewDay >= latestDay}
              onClick={() => viewDay !== null && mission.selectViewDay(viewDay + 1)}
            >
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="mission-bar__timeline">
          <p className="eyebrow">
            Mission timeline
            {alertDays.size > 0 && <span className="timeline-key"><span className="timeline__alert" aria-hidden="true" /> alert detected</span>}
          </p>
          {astronaut
            ? <MissionTimeline astronaut={astronaut} viewDay={viewDay} latestDay={latestDay} alertDays={alertDays} onSelect={mission.selectViewDay} />
            : <div className="timeline timeline--empty" aria-hidden="true" />}
          <p className="mission-bar__caption mono" role="status">{caption}</p>
        </div>

        {source.kind === 'mock' ? (
          <button type="button" className="button button--secondary mission-bar__demo" onClick={onOpenDemo}>
            <FlaskConical size={16} aria-hidden="true" />
            <span>Synthetic demo</span>
          </button>
        ) : (
          <p className="tag mission-bar__demo"><FlaskConical size={13} aria-hidden="true" /> API · synthetic mission data</p>
        )}
      </div>

      {isHistorical && astronaut && viewDay !== null && latestDay !== null && (
        <div className="history-banner" role="status">
          <div className="history-banner__inner">
            <History size={18} aria-hidden="true" />
            <p>
              <strong>Historical view: Day {viewDay}.</strong>{' '}
              Observations recorded after {asOf ? formatUtcDateTime(asOf) : `Day ${viewDay}`} are not shown.
            </p>
            <button type="button" className="button button--secondary button--small" onClick={() => mission.selectViewDay(null)}>
              Return to latest (Day {latestDay})
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
