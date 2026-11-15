import { useState, useSyncExternalStore } from 'react'
import { RotateCcw } from 'lucide-react'
import { useMission } from '../hooks/MissionContext'
import { demoControls } from '../services/mock/demoControls'
import type { DemoAnalysis, DemoLoading, DemoSaveOutcome } from '../services/mock/demoControls'
import { resetMockData } from '../services/mockHealthDataSource'
import { Callout, Dialog } from './ui'

interface Choice<T extends string> {
  value: T
  label: string
  detail: string
}

const ANALYSIS: Choice<DemoAnalysis>[] = [
  { value: 'contract', label: 'Contract fixtures', detail: 'The single synthetic warning from the shared examples.' },
  { value: 'samples', label: 'Presentation samples', detail: 'Adds labeled samples for the other attention levels and the resolved status.' },
  { value: 'not_implemented', label: 'Analysis not implemented', detail: 'References and alerts unavailable, as before the backend engines exist.' },
]

const LOADING: Choice<DemoLoading>[] = [
  { value: 'normal', label: 'Normal', detail: 'Requests answer quickly.' },
  { value: 'slow', label: 'Slow responses', detail: 'Every request takes about two seconds.' },
  { value: 'fail', label: 'Requests fail', detail: 'Every request fails until you switch back, then use “Try again”.' },
]

const SAVE: Choice<DemoSaveOutcome>[] = [
  { value: 'success', label: 'Succeeds', detail: 'The entry is stored in this page session.' },
  { value: 'validation', label: 'Rejected field', detail: 'The data source rejects the sleep value (422).' },
  { value: 'network', label: 'Connection failure', detail: 'The request never reaches the data source.' },
  { value: 'timeout', label: 'Unconfirmed', detail: 'The save may have happened, but no confirmation arrives.' },
]

function ChoiceGroup<T extends string>({ legend, hint, name, value, choices, onChange }: {
  legend: string
  hint: string
  name: string
  value: T
  choices: Choice<T>[]
  onChange: (value: T) => void
}) {
  return (
    <fieldset className="choice-group">
      <legend>{legend}</legend>
      <p className="choice-group__hint">{hint}</p>
      {choices.map((choice) => (
        <label key={choice.value} className="choice">
          <input type="radio" name={name} checked={choice.value === value} onChange={() => onChange(choice.value)} />
          <span>
            <span className="choice__label">{choice.label}</span>
            <span className="choice__detail">{choice.detail}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}

/** Review tools for the mock data source. Not product behavior; absent with the live API. */
export function DemoScenarios({ open, onClose }: { open: boolean; onClose: () => void }) {
  const controls = useSyncExternalStore(demoControls.subscribe, demoControls.get)
  const { refresh } = useMission()
  const [restored, setRestored] = useState(false)

  return (
    <Dialog
      open={open}
      title="Demo scenarios"
      wide
      onClose={() => {
        setRestored(false)
        onClose()
      }}
      footer={<button type="button" className="button button--primary" onClick={onClose}>Done</button>}
    >
      <p>
        Every observation in this prototype is synthetic. These switches belong to the mock data source and let you
        review states the seed data does not produce by itself. They are not part of AstroHealth and reset when the
        page reloads.
      </p>
      <div className="choice-groups">
        <ChoiceGroup legend="Alert analysis" hint="What the analysis reports." name="demo-analysis" value={controls.analysis} choices={ANALYSIS} onChange={(analysis) => demoControls.set({ analysis })} />
        <ChoiceGroup legend="Loading" hint="How reads behave." name="demo-loading" value={controls.loading} choices={LOADING} onChange={(loading) => demoControls.set({ loading })} />
        <ChoiceGroup legend="Next journal save" hint="Applies once, then returns to “Succeeds”." name="demo-save" value={controls.nextSave} choices={SAVE} onChange={(nextSave) => demoControls.set({ nextSave })} />
      </div>
      <div className="demo-reset">
        <button
          type="button"
          className="button button--secondary"
          onClick={() => {
            resetMockData()
            demoControls.reset()
            refresh()
            setRestored(true)
          }}
        >
          <RotateCcw size={16} aria-hidden="true" /> Restore seed data
        </button>
        <p className="demo-reset__hint">Discards journal entries saved in this session and resets the switches.</p>
      </div>
      {restored && <Callout tone="success" title="Seed data restored" role="status" compact />}
    </Dialog>
  )
}
