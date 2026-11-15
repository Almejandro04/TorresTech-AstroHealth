/**
 * Review switches for the mock data source. They let a reviewer reach states the synthetic
 * seed does not produce by itself (analysis not implemented, failed requests, rejected saves).
 * They are scaffolding for the demonstration, not product behavior, and are only rendered
 * while the mock source is selected.
 */
export type DemoAnalysis = 'contract' | 'samples' | 'not_implemented'
export type DemoLoading = 'normal' | 'slow' | 'fail'
export type DemoSaveOutcome = 'success' | 'validation' | 'network' | 'timeout'

export interface DemoControls {
  analysis: DemoAnalysis
  loading: DemoLoading
  /** Applies to the next journal save only, then returns to `success`. */
  nextSave: DemoSaveOutcome
}

const defaults: DemoControls = { analysis: 'contract', loading: 'normal', nextSave: 'success' }

let state: DemoControls = defaults
const listeners = new Set<() => void>()

export const demoControls = {
  get: (): DemoControls => state,
  set(patch: Partial<DemoControls>) {
    state = { ...state, ...patch }
    listeners.forEach((listener) => listener())
  },
  reset() {
    state = defaults
    listeners.forEach((listener) => listener())
  },
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  },
}
