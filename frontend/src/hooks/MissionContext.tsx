import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from 'react'
import type { ReactNode } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { healthDataSource } from '../services'
import type { HealthDataSource } from '../services'
import { demoControls } from '../services/mock/demoControls'
import { missionDayEndIso } from '../lib/time'
import type { AlertListResponse, ApiResponse, Astronaut, HealthSummary, PaginatedResponse } from '../types/health'
import { useResource } from './useResource'
import type { Resource } from './useResource'

/** Selections that follow the user across views and survive a reload, kept in the URL. */
const SHARED_PARAMS = ['astronaut', 'day', 'range', 'from', 'to'] as const

export interface MissionValue {
  source: HealthDataSource
  profiles: Resource<PaginatedResponse<Astronaut>>
  /** Selected fictional profile; `null` while profiles load or when the requested ID is unknown. */
  astronaut: Astronaut | null
  /** An ID was requested in the URL that the data source does not list. */
  unknownAstronautId: string | null
  /** Summary with no cutoff: defines the latest recorded mission day. */
  latest: Resource<ApiResponse<HealthSummary>>
  /** Summary for the mission view (the selected day, or the latest). Every view reads this. */
  view: Resource<ApiResponse<HealthSummary>>
  alerts: Resource<AlertListResponse>
  latestDay: number | null
  viewDay: number | null
  isHistorical: boolean
  /** Explicit observation cutoff passed to the data source; `undefined` means latest. */
  asOf: string | undefined
  revision: number
  refresh: () => void
  selectAstronaut: (astronautId: string) => void
  selectViewDay: (day: number | null) => void
  /** Route target that keeps the shared selections. */
  linkTo: (pathname: string, extra?: Record<string, string>) => { pathname: string; search: string }
}

const MissionContext = createContext<MissionValue | null>(null)

export function useMission(): MissionValue {
  const value = useContext(MissionContext)
  if (!value) throw new Error('useMission must be used inside MissionProvider.')
  return value
}

const parseDay = (raw: string | null): number | null => {
  if (raw === null || !/^\d{1,3}$/.test(raw)) return null
  return Number(raw)
}

export function MissionProvider({ children, source = healthDataSource }: { children: ReactNode; source?: HealthDataSource }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [revision, refresh] = useReducer((count: number) => count + 1, 0)

  // Demo switches that change what the mock returns reload every resource.
  const demoRef = useRef(demoControls.get())
  useEffect(() => {
    if (source.kind !== 'mock') return
    return demoControls.subscribe(() => {
      const next = demoControls.get()
      const changed = next.analysis !== demoRef.current.analysis || next.loading !== demoRef.current.loading
      demoRef.current = next
      if (changed) refresh()
    })
  }, [source])

  const profiles = useResource('profiles', () => source.getAstronauts(), revision)
  const requestedId = searchParams.get('astronaut')
  const profileList = profiles.status === 'ready' ? profiles.data.data : null
  const astronaut = profileList
    ? (requestedId ? profileList.find((profile) => profile.astronaut_id === requestedId) : profileList[0]) ?? null
    : null
  const unknownAstronautId = profileList && requestedId && !astronaut ? requestedId : null
  const astronautId = astronaut?.astronaut_id ?? null

  const latest = useResource(
    astronautId ? `summary:${astronautId}:latest` : null,
    () => source.getSummary(astronautId ?? ''),
    revision,
  )
  const latestDay = latest.status === 'ready' ? latest.data.data.mission_day : null

  // A historical view needs a day strictly before the latest one; anything else is the latest view.
  const requestedDay = parseDay(searchParams.get('day'))
  const historicalDay =
    astronaut && latestDay !== null && requestedDay !== null && requestedDay >= 1 && requestedDay < latestDay
      ? requestedDay
      : null
  const asOf = astronaut && historicalDay !== null ? missionDayEndIso(astronaut.mission_start_date, historicalDay) : undefined

  const historical = useResource(
    astronautId && asOf ? `summary:${astronautId}:${asOf}` : null,
    () => source.getSummary(astronautId ?? '', { as_of: asOf }),
    revision,
  )
  const view = asOf ? historical : latest

  const alerts = useResource(
    astronautId && latest.status === 'ready' ? `alerts:${astronautId}:${asOf ?? 'latest'}` : null,
    () => source.getAlerts(astronautId ?? '', { as_of: asOf, limit: 1000 }),
    revision,
  )

  const linkTo = useCallback<MissionValue['linkTo']>(
    (pathname, extra) => {
      const next = new URLSearchParams()
      for (const key of SHARED_PARAMS) {
        const value = searchParams.get(key)
        if (value !== null) next.set(key, value)
      }
      for (const [key, value] of Object.entries(extra ?? {})) next.set(key, value)
      const search = next.toString()
      return { pathname, search: search ? `?${search}` : '' }
    },
    [searchParams],
  )

  /** Detail routes (an alert, a journal day) belong to one astronaut and one view: leave them. */
  const sectionPath = `/${location.pathname.split('/')[1] ?? 'dashboard'}`

  const selectAstronaut = useCallback(
    (nextId: string) => {
      const next = new URLSearchParams()
      next.set('astronaut', nextId)
      for (const key of ['range', 'from', 'to']) {
        const value = searchParams.get(key)
        if (value !== null) next.set(key, value)
      }
      navigate({ pathname: sectionPath, search: `?${next.toString()}` })
    },
    [navigate, searchParams, sectionPath],
  )

  const selectViewDay = useCallback(
    (day: number | null) => {
      const next = new URLSearchParams(searchParams)
      next.delete('entry')
      if (day === null || (latestDay !== null && day >= latestDay)) next.delete('day')
      else next.set('day', String(day))
      const search = next.toString()
      navigate({ pathname: sectionPath, search: search ? `?${search}` : '' })
    },
    [navigate, searchParams, sectionPath, latestDay],
  )

  const value = useMemo<MissionValue>(
    () => ({
      source,
      profiles,
      astronaut,
      unknownAstronautId,
      latest,
      view,
      alerts,
      latestDay,
      viewDay: historicalDay ?? latestDay,
      isHistorical: historicalDay !== null,
      asOf,
      revision,
      refresh,
      selectAstronaut,
      selectViewDay,
      linkTo,
    }),
    [source, profiles, astronaut, unknownAstronautId, latest, view, alerts, latestDay, historicalDay, asOf, revision, selectAstronaut, selectViewDay, linkTo],
  )

  return <MissionContext.Provider value={value}>{children}</MissionContext.Provider>
}
