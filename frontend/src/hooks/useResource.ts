import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { toHealthDataError } from '../services'
import type { HealthDataError } from '../services'

/**
 * Loading, ready, and failed are distinct states, and a failure never keeps showing earlier
 * data as if it were current. While the same resource is being refreshed, the previous result
 * stays on screen (flagged `refreshing`) so the layout does not jump.
 */
export type Resource<T> =
  | { status: 'idle'; retry: () => void }
  | { status: 'loading'; retry: () => void }
  | { status: 'ready'; data: T; refreshing: boolean; retry: () => void }
  | { status: 'error'; error: HealthDataError; retry: () => void }

type Stored<T> =
  | { key: string | null; status: 'idle' | 'loading' }
  | { key: string; status: 'ready'; data: T; refreshing: boolean }
  | { key: string; status: 'error'; error: HealthDataError }

/**
 * @param key identifies what is loaded; `null` means the inputs are not known yet.
 * @param revision bump it to reload the same resource (after a write, or a demo switch).
 */
export function useResource<T>(key: string | null, load: () => Promise<T>, revision = 0): Resource<T> {
  const [stored, setStored] = useState<Stored<T>>({ key, status: key === null ? 'idle' : 'loading' })
  const [attempt, retryAttempt] = useReducer((count: number) => count + 1, 0)
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    if (key === null) {
      setStored({ key: null, status: 'idle' })
      return
    }
    let current = true
    setStored((previous) =>
      previous.key === key && previous.status === 'ready' ? { ...previous, refreshing: true } : { key, status: 'loading' },
    )
    loadRef.current().then(
      (data) => {
        if (current) setStored({ key, status: 'ready', data, refreshing: false })
      },
      (error: unknown) => {
        if (current) setStored({ key, status: 'error', error: toHealthDataError(error) })
      },
    )
    return () => {
      current = false
    }
  }, [key, revision, attempt])

  const retry = useCallback(() => retryAttempt(), [])

  // A result for another key is never shown: it would belong to a different astronaut or cutoff.
  if (key === null) return { status: 'idle', retry }
  if (stored.key !== key) return { status: 'loading', retry }
  if (stored.status === 'ready') return { status: 'ready', data: stored.data, refreshing: stored.refreshing, retry }
  if (stored.status === 'error') return { status: 'error', error: stored.error, retry }
  return { status: 'loading', retry }
}
