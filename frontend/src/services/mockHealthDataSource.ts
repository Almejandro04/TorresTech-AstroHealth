import { HealthDataError } from './errors'
import type { HealthDataSource } from './healthDataSource'
import { demoControls } from './mock/demoControls'
import { buildSummary, createSeedStore, listAlerts, listAstronauts, listJournal, listReadings, upsertJournal } from './mock/engine'

/**
 * Asynchronous mock of the contract over the synthetic seed. Journal writes live in this
 * module's memory for the current page session only: reloading restores the seed, and nothing
 * is ever sent to a server.
 */
let store = createSeedStore()

const READ_LATENCY_MS = 120
const WRITE_LATENCY_MS = 450
const SLOW_LATENCY_MS = 1800

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
const latency = (base: number) => (demoControls.get().loading === 'slow' ? SLOW_LATENCY_MS : base)

async function read<T>(produce: () => T): Promise<T> {
  await wait(latency(READ_LATENCY_MS))
  if (demoControls.get().loading === 'fail') {
    throw new HealthDataError({ kind: 'network', message: 'The mock data source is set to fail requests.' })
  }
  return structuredClone(produce())
}

/** Restores the synthetic seed, discarding journal entries saved during this session. */
export function resetMockData() {
  store = createSeedStore()
}

export const mockHealthDataSource: HealthDataSource = {
  kind: 'mock',
  getAstronauts: () => read(() => listAstronauts(store)),
  getSummary: (astronautId, query) => read(() => buildSummary(store, astronautId, query, demoControls.get().analysis)),
  getReadings: (astronautId, query) => read(() => listReadings(store, astronautId, query)),
  getJournal: (astronautId, query) => read(() => listJournal(store, astronautId, query)),
  getAlerts: (astronautId, query) => read(() => listAlerts(store, astronautId, query, demoControls.get().analysis)),

  async saveJournal(astronautId, entry) {
    const { nextSave, loading } = demoControls.get()
    await wait(latency(WRITE_LATENCY_MS))
    if (nextSave !== 'success') demoControls.set({ nextSave: 'success' })

    if (nextSave === 'network' || loading === 'fail') {
      throw new HealthDataError({ kind: 'network', message: 'The mock data source did not receive the request.' })
    }
    if (nextSave === 'validation') {
      throw new HealthDataError({
        kind: 'validation',
        status: 422,
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed.',
        details: [{ field: 'body.sleep_hours_last_night', message: 'Must be between 0 and 24.' }],
      })
    }
    const result = upsertJournal(store, astronautId, entry)
    if (nextSave === 'timeout') {
      // The write was applied but its confirmation never arrived: the client cannot know.
      throw new HealthDataError({ kind: 'timeout', message: 'The mock data source did not confirm the save in time.' })
    }
    return structuredClone(result)
  },
}
