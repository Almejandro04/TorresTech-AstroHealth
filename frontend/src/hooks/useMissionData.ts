import { useEffect, useReducer, useState } from 'react'
import { healthDataSource } from '../services'
import type { HealthDataSource } from '../services'
import type { ApiResponse, HealthSummary } from '../types/health'

type MissionState =
  | { status: 'loading' }
  | { status: 'ready'; response: ApiResponse<HealthSummary> }
  | { status: 'error'; message: string }

export function useMissionData(source: HealthDataSource = healthDataSource) {
  const [state, setState] = useState<MissionState>({ status: 'loading' })
  const [attempt, retry] = useReducer((value: number) => value + 1, 0)

  useEffect(() => {
    let current = true
    setState({ status: 'loading' })

    async function load() {
      const profiles = await source.getAstronauts()
      const profile = profiles.data[0]
      if (!profile) throw new Error('No mission profile is available yet.')
      const response = await source.getSummary(profile.astronaut_id)
      if (current) setState({ status: 'ready', response })
    }

    void load().catch((error: unknown) => {
      if (current) {
        setState({ status: 'error', message: error instanceof Error ? error.message : 'Mission information could not be loaded.' })
      }
    })

    return () => { current = false }
  }, [source, attempt])

  return { state, retry }
}
