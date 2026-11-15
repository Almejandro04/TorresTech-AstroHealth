import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ChevronLeft, ChevronRight, CircleAlert, FileText, LoaderCircle, RotateCcw } from 'lucide-react'
import { useBlocker, useSearchParams } from 'react-router-dom'
import { Callout, Dialog, ErrorState, LoadingBlock, PageHeader, Section, Tag } from '../components/ui'
import { useMission } from '../hooks/MissionContext'
import { loadHistory } from '../hooks/useHistory'
import { useResource } from '../hooks/useResource'
import { MOOD_LABELS, MOOD_SCORES, describeValue } from '../lib/metrics'
import { formatUtcDate, formatUtcShortDate, missionDayStartMs } from '../lib/time'
import { HealthDataError, toHealthDataError } from '../services'
import { buildJournalInput } from '../services/journalDefaults'
import { appConfig } from '../services/config'
import type { Astronaut, HealthJournal, MoodScore } from '../types/health'

const NOTES_LIMIT = 2000

interface Draft {
  sleep: string
  mood: MoodScore | null
  notes: string
}
type FieldName = 'sleep' | 'mood' | 'notes'
type FieldErrors = Partial<Record<FieldName | 'form', string>>

type SaveState =
  | { status: 'idle' }
  | { status: 'saving' }
  | { status: 'saved'; outcome: 'created' | 'updated'; entry: HealthJournal }
  | { status: 'failed'; error: HealthDataError }

const draftOf = (entry: HealthJournal | null): Draft => ({
  sleep: entry?.sleep_hours_last_night === null || entry === null ? '' : String(entry.sleep_hours_last_night),
  mood: entry?.mood_score ?? null,
  notes: entry?.notes ?? '',
})
const sameDraft = (a: Draft, b: Draft) => a.sleep.trim() === b.sleep.trim() && a.mood === b.mood && a.notes.trim() === b.notes.trim()

/** Accepts "7.5" and "7,5"; returns `undefined` when the text is not a duration from 0 to 24. */
function parseSleep(text: string): number | null | undefined {
  const trimmed = text.trim()
  if (trimmed === '') return null
  if (!/^\d{1,2}([.,]\d{1,2})?$/.test(trimmed)) return undefined
  const value = Number(trimmed.replace(',', '.'))
  return value >= 0 && value <= 24 ? value : undefined
}

function validate(draft: Draft): FieldErrors {
  const errors: FieldErrors = {}
  const sleep = parseSleep(draft.sleep)
  const notes = draft.notes.trim()
  if (sleep === undefined) errors.sleep = 'Enter hours from 0 to 24, for example 7.5.'
  if (notes.length > NOTES_LIMIT) errors.notes = `The note has ${notes.length.toLocaleString('en-US')} characters. Shorten it to ${NOTES_LIMIT.toLocaleString('en-US')} or fewer.`
  if (!errors.sleep && !errors.notes && sleep === null && draft.mood === null && notes === '') {
    errors.form = 'Add sleep, mood, or a note before saving.'
  }
  return errors
}

/** Turns the data source's field paths into guidance next to the matching field. */
function serverFieldErrors(error: HealthDataError): FieldErrors {
  const errors: FieldErrors = {}
  for (const detail of error.details) {
    if (detail.field === 'body.sleep_hours_last_night') errors.sleep = 'The data source did not accept this value. Enter hours from 0 to 24.'
    else if (detail.field === 'body.mood_score') errors.mood = 'Choose a mood from 1 (Very low) to 5 (Very high).'
    else if (detail.field === 'body.notes') errors.notes = `Shorten the note to ${NOTES_LIMIT.toLocaleString('en-US')} characters or fewer.`
    else if (detail.field === 'body.mission_day' || detail.field === 'body.timestamp') errors.form = 'This entry’s day does not match its date. Select the day again, then save.'
    else if (detail.field === 'body') errors.form = 'Add sleep, mood, or a note before saving.'
  }
  if (Object.keys(errors).length === 0) errors.form = 'Some information was not accepted. Review the entry and save again.'
  return errors
}

interface SaveConfirmation {
  astronautId: string
  outcome: 'created' | 'updated'
  entry: HealthJournal
}

interface JournalFormProps {
  astronaut: Astronaut
  day: number
  entry: HealthJournal | null
  isPastDay: boolean
  viewDay: number | null
  isHistorical: boolean
  onSaved: (confirmation: SaveConfirmation) => void
  onEdit: () => void
}

function JournalForm({ astronaut, day, entry, isPastDay, viewDay, isHistorical, onSaved, onEdit }: JournalFormProps) {
  const { source, refresh } = useMission()
  const [saved, setSaved] = useState<HealthJournal | null>(entry)
  const [draft, setDraft] = useState<Draft>(() => draftOf(entry))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [save, setSave] = useState<SaveState>({ status: 'idle' })
  const sleepId = useId()
  const notesId = useId()
  const moodId = useId()
  const feedbackRef = useRef<HTMLDivElement>(null)
  const sleepRef = useRef<HTMLInputElement>(null)
  const notesRef = useRef<HTMLTextAreaElement>(null)

  // Wait for React to render feedback before moving keyboard focus to it.
  useEffect(() => {
    if (save.status === 'failed') feedbackRef.current?.focus()
  }, [save.status])

  const saving = save.status === 'saving'
  const newEntrySetupPending = source.kind === 'api' && !saved && !appConfig.newJournalDefaults
  const dirty = !sameDraft(draft, draftOf(saved))
  const notesLength = draft.notes.trim().length
  const dateLabel = formatUtcDate(missionDayStartMs(astronaut.mission_start_date, day))

  // Unsaved changes are never dropped silently: leaving the entry asks first.
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty && (currentLocation.pathname !== nextLocation.pathname || currentLocation.search !== nextLocation.search),
  )
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const edit = (patch: Partial<Draft>) => {
    onEdit()
    setDraft((current) => ({ ...current, ...patch }))
    setErrors({})
    if (save.status !== 'saving') setSave({ status: 'idle' })
  }

  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    if (saving) return
    if (newEntrySetupPending) return
    const found = validate(draft)
    if (Object.keys(found).length > 0) {
      setErrors(found)
      setSave({ status: 'idle' })
      if (found.sleep) sleepRef.current?.focus()
      else if (found.notes) notesRef.current?.focus()
      else feedbackRef.current?.focus()
      return
    }
    setErrors({})
    setSave({ status: 'saving' })
    const notes = draft.notes.trim()
    const input = buildJournalInput(astronaut, day, saved, { sleep: parseSleep(draft.sleep) ?? null, mood: draft.mood, notes: notes === '' ? null : notes }, source.kind === 'api' ? appConfig.newJournalDefaults ?? undefined : undefined)
    try {
      const result = await source.saveJournal(astronaut.astronaut_id, input)
      if (saved && result.response.data.journal_id !== saved.journal_id) {
        throw new HealthDataError({ kind: 'timeout', code: 'INVALID_RESPONSE', message: 'The correction did not confirm the original entry identity.' })
      }
      setSaved(result.response.data)
      setDraft(draftOf(result.response.data))
      setSave({ status: 'saved', outcome: result.outcome, entry: result.response.data })
      onSaved({ astronautId: astronaut.astronaut_id, outcome: result.outcome, entry: result.response.data })
      refresh()
    } catch (caught) {
      const error = toHealthDataError(caught)
      setSave({ status: 'failed', error })
      if (error.kind === 'validation') setErrors(serverFieldErrors(error))
    }
  }

  const cancel = () => {
    setDraft(draftOf(saved))
    setErrors({})
    setSave({ status: 'idle' })
  }

  const failure = save.status === 'failed' ? save.error : null
  const retryAction = (
    <button type="button" className="button button--secondary" onClick={() => void submit()}>
      <RotateCcw size={16} aria-hidden="true" /> Try again
    </button>
  )

  return (
    <form className="journal-form" onSubmit={(event) => void submit(event)} noValidate aria-busy={saving}>
      <div className="journal-form__head">
        <h2>Day {day} entry</h2>
        <p className="mono">{astronaut.name} · {dateLabel} (UTC)</p>
        <p className="journal-form__state">
          {saved
            ? <><Tag>Recorded entry</Tag> <span>Saving changes keeps the same entry <span className="mono">{saved.journal_id}</span>.</span></>
            : <><Tag>New entry</Tag> <span>Nothing is recorded for this day yet. No value is assumed.</span></>}
        </p>
      </div>

      {newEntrySetupPending && <Callout tone="info" title="New-entry setup pending"><p>New entries are not enabled for this mission yet. You can still select a recorded day and correct its entry.</p></Callout>}

      {isPastDay && (
        <Callout tone="info" title={`You are editing Day ${day}, a past day`} compact>
          <p>
            {isHistorical ? `The mission view is the historical Day ${viewDay}.` : `The mission view is Day ${viewDay}.`}{' '}
            Saving changes Day {day} only.
          </p>
        </Callout>
      )}

      <fieldset className="journal-form__fields" disabled={saving}>
        <legend className="visually-hidden">Day {day} self-report</legend>

        <div className="field">
          <label className="field__label" htmlFor={sleepId}>Sleep last night <span className="field__optional">optional</span></label>
          <p className="field__help" id={`${sleepId}-help`}>Hours slept in the sleep period that ended on Day {day}. From 0 to 24; decimals are fine.</p>
          <div className="input-suffix">
            <input
              ref={sleepRef}
              id={sleepId}
              className="input"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={draft.sleep}
              aria-describedby={`${sleepId}-help${errors.sleep ? ` ${sleepId}-error` : ''}`}
              aria-invalid={errors.sleep ? true : undefined}
              onChange={(event) => edit({ sleep: event.target.value })}
            />
            <span aria-hidden="true">hours</span>
          </div>
          {errors.sleep && <p className="field__error" id={`${sleepId}-error`}><CircleAlert size={15} aria-hidden="true" /> {errors.sleep}</p>}
        </div>

        <fieldset className="field" aria-describedby={`${moodId}-help${errors.mood ? ` ${moodId}-error` : ''}`}>
          <legend className="field__label">Mood <span className="field__optional">optional</span></legend>
          <p className="field__help" id={`${moodId}-help`}>How you feel today, from 1 to 5. A self-report scale, not a clinical score.</p>
          <div className="mood">
            {MOOD_SCORES.map((score) => (
              <label key={score} className="mood__option">
                <input type="radio" name={`${moodId}-mood`} value={score} checked={draft.mood === score} onChange={() => edit({ mood: score })} />
                <span><span className="mood__score">{score}</span><span className="mood__label">{MOOD_LABELS[score]}</span></span>
              </label>
            ))}
          </div>
          {draft.mood !== null && (
            <button type="button" className="button button--quiet button--small" onClick={() => edit({ mood: null })}>Clear mood</button>
          )}
          {errors.mood && <p className="field__error" id={`${moodId}-error`}><CircleAlert size={15} aria-hidden="true" /> {errors.mood}</p>}
        </fieldset>

        <div className="field">
          <label className="field__label" htmlFor={notesId}>Notes <span className="field__optional">optional</span></label>
          <p className="field__help" id={`${notesId}-help`}>Plain text, up to {NOTES_LIMIT.toLocaleString('en-US')} characters.</p>
          <textarea
            ref={notesRef}
            id={notesId}
            className="input input--area"
            rows={5}
            value={draft.notes}
            aria-describedby={`${notesId}-help ${notesId}-count${errors.notes ? ` ${notesId}-error` : ''}`}
            aria-invalid={errors.notes ? true : undefined}
            onChange={(event) => edit({ notes: event.target.value })}
          />
          <p className={`field__count mono${notesLength > NOTES_LIMIT ? ' is-over' : ''}`} id={`${notesId}-count`}>
            {notesLength.toLocaleString('en-US')} / {NOTES_LIMIT.toLocaleString('en-US')} characters
          </p>
          {errors.notes && <p className="field__error" id={`${notesId}-error`}><CircleAlert size={15} aria-hidden="true" /> {errors.notes}</p>}
        </div>
      </fieldset>

      <div className="journal-form__feedback" ref={feedbackRef} tabIndex={-1}>
        {errors.form && <Callout tone="critical" title="The entry was not saved" role="alert" icon={CircleAlert}><p>{errors.form}</p></Callout>}
        {!errors.form && failure?.kind === 'validation' && (
          <Callout tone="critical" title="The entry was not saved" role="alert" icon={CircleAlert}>
            <p>The data source did not accept part of the entry. Correct the highlighted field and save again. Your text is still here.</p>
          </Callout>
        )}
        {failure?.kind === 'network' && (
          <Callout tone="critical" title="The entry was not saved" role="alert" icon={CircleAlert} actions={retryAction}>
            <p>The data source could not be reached, so nothing was sent. Your entry is still here.</p>
          </Callout>
        )}
        {failure?.kind === 'timeout' && (
          <Callout tone="warning" title="The save could not be confirmed" role="alert" actions={retryAction}>
            <p>No confirmation arrived, so the entry may or may not be saved. Your text is still here. Trying again is safe: each day has a single entry, so no duplicate is created.</p>
          </Callout>
        )}
        {failure?.kind === 'not_found' && (
          <Callout tone="critical" title="The entry was not saved" role="alert" icon={CircleAlert}>
            <p>This astronaut profile is no longer available in the data source. Your text is still here; choose another profile only after copying it.</p>
          </Callout>
        )}
        {failure && (failure.kind === 'server' || failure.kind === 'conflict') && (
          <Callout tone="critical" title="The entry was not saved" role="alert" icon={CircleAlert} actions={retryAction}>
            <p>The data source reported a problem. Your entry is still here.</p>
          </Callout>
        )}
      </div>

      <div className="journal-form__actions">
        <button type="submit" className="button button--primary" aria-disabled={saving || !dirty || newEntrySetupPending} disabled={saving || !dirty || newEntrySetupPending}>
          {saving && <LoaderCircle className="spin" size={16} aria-hidden="true" />}
          {saving ? 'Saving…' : saved ? 'Save changes' : 'Save entry'}
        </button>
        <button type="button" className="button button--secondary" onClick={cancel} disabled={saving || !dirty}>Cancel</button>
        <p className="journal-form__hint" role="status">
          {saving ? 'Saving, please wait.' : dirty ? 'Unsaved changes. Cancel restores the last saved values.' : 'No unsaved changes.'}
        </p>
      </div>

      <Dialog
        open={blocker.state === 'blocked'}
        title="Discard unsaved changes?"
        onClose={() => blocker.reset?.()}
        footer={
          <>
            <button type="button" className="button button--primary" autoFocus onClick={() => blocker.reset?.()}>Keep editing</button>
            <button type="button" className="button button--secondary" onClick={() => blocker.proceed?.()}>Discard changes</button>
          </>
        }
      >
        <p>The Day {day} entry for {astronaut.name} has changes that are not saved. Leaving now discards them.</p>
      </Dialog>
    </form>
  )
}

export function JournalPage() {
  const { astronaut, source, asOf, view, viewDay, latestDay, isHistorical, revision, unknownAstronautId } = useMission()
  const [searchParams, setSearchParams] = useSearchParams()
  const dayFieldId = useId()
  const [confirmation, setConfirmation] = useState<SaveConfirmation | null>(null)
  const confirmationRef = useRef<HTMLDivElement>(null)

  // The form may remount when the new cutoff reloads history. Keep confirmed
  // write feedback outside that loading subtree so it remains visible/focused.
  useEffect(() => {
    if (confirmation) confirmationRef.current?.focus()
  }, [confirmation])

  const viewReady = view.status === 'ready'
  const entries = useResource(
    astronaut && viewReady ? `journal:${astronaut.astronaut_id}:${asOf ?? 'latest'}` : null,
    () => loadHistory(source, astronaut?.astronaut_id ?? '', { as_of: asOf }).then((history) => history.journal),
    revision,
  )

  // Days that can hold an entry: every day up to the mission view, plus the next day when
  // looking at the latest data (the demo mission advances when its next entry is recorded).
  const lastSelectable = astronaut
    ? isHistorical && viewDay !== null ? viewDay : Math.min(astronaut.planned_duration_days, (latestDay ?? 0) + 1)
    : 0
  const requested = Number(searchParams.get('entry'))
  const selectedDay = Number.isInteger(requested) && requested >= 1 && requested <= lastSelectable ? requested : Math.max(1, viewDay ?? 1)
  const dayOptions = Array.from({ length: lastSelectable }, (_, index) => lastSelectable - index)
  const journal = entries.status === 'ready' ? entries.data : []
  const entryFor = (day: number) => journal.find((entry) => entry.mission_day === day) ?? null

  const selectDay = (day: number) => {
    setConfirmation(null)
    const next = new URLSearchParams(searchParams)
    next.set('entry', String(day))
    setSearchParams(next)
  }

  return (
    <>
      <PageHeader title="Journal" lead="Daily self-report of sleep, mood, and notes. One entry per mission day, which you can correct." />

      {confirmation?.astronautId === astronaut?.astronaut_id && confirmation?.entry.mission_day === selectedDay && (
        <div ref={confirmationRef} tabIndex={-1} className="journal-form__feedback">
          <Callout tone="success" title="Journal saved" role="status">
            <p>Day {confirmation.entry.mission_day} entry <span className="mono">{confirmation.entry.journal_id}</span>{' '}
              {confirmation.outcome === 'created' ? 'was created.' : 'was updated; its ID is unchanged.'}</p>
            {source.kind === 'mock' && <p>Demo data source: kept in this page session only. Nothing was sent to a server.</p>}
          </Callout>
        </div>
      )}

      {unknownAstronautId && <Callout tone="warning" title="Astronaut profile not found"><p>Choose a profile in the mission bar.</p></Callout>}
      {view.status === 'error' && <ErrorState error={view.error} subject="the mission summary" onRetry={view.retry} />}
      {entries.status === 'error' && <ErrorState error={entries.error} subject="the journal" onRetry={entries.retry} />}
      {(view.status === 'loading' || entries.status === 'loading') && <LoadingBlock label="Loading journal…" rows={4} />}

      {astronaut && entries.status === 'ready' && (
        <div className="journal">
          <div className="journal__main">
            <div className="field journal__day">
              <label className="field__label" htmlFor={dayFieldId}>Entry day</label>
              <div className="stepper">
                <button type="button" className="icon-button stepper__step" aria-label="Previous day" disabled={selectedDay <= 1} onClick={() => selectDay(selectedDay - 1)}>
                  <ChevronLeft size={18} aria-hidden="true" />
                </button>
                <select id={dayFieldId} className="select" value={selectedDay} onChange={(event) => selectDay(Number(event.target.value))}>
                  {dayOptions.map((day) => (
                    <option key={day} value={day}>
                      Day {day} · {formatUtcShortDate(missionDayStartMs(astronaut.mission_start_date, day))} · {entryFor(day) ? 'recorded' : 'no entry yet'}
                    </option>
                  ))}
                </select>
                <button type="button" className="icon-button stepper__step" aria-label="Next day" disabled={selectedDay >= lastSelectable} onClick={() => selectDay(selectedDay + 1)}>
                  <ChevronRight size={18} aria-hidden="true" />
                </button>
              </div>
            </div>

            <JournalForm
              key={`${astronaut.astronaut_id}:${selectedDay}`}
              astronaut={astronaut}
              day={selectedDay}
              entry={entryFor(selectedDay)}
              isPastDay={viewDay !== null && selectedDay < viewDay}
              viewDay={viewDay}
              isHistorical={isHistorical}
              onSaved={setConfirmation}
              onEdit={() => setConfirmation(null)}
            />
          </div>

          <Section title="Recorded entries" note={isHistorical ? `Up to Day ${viewDay}` : 'Newest first'} busy={entries.refreshing}>
            {journal.length === 0 ? (
              <p className="readout__muted">No journal entries recorded yet. The first one you save appears here.</p>
            ) : (
              <ul className="entry-list">
                {[...journal].reverse().map((entry) => (
                  <li key={entry.journal_id}>
                    <button
                      type="button"
                      className={`entry-list__item${entry.mission_day === selectedDay ? ' is-selected' : ''}`}
                      aria-current={entry.mission_day === selectedDay ? 'true' : undefined}
                      onClick={() => selectDay(entry.mission_day)}
                    >
                      <span className="entry-list__day">Day {entry.mission_day}<span className="mono">{formatUtcShortDate(entry.timestamp)}</span></span>
                      <span>{entry.sleep_hours_last_night === null ? 'Sleep not recorded' : describeValue('sleep_hours_last_night', entry.sleep_hours_last_night)}</span>
                      <span>{entry.mood_score === null ? 'Mood not recorded' : describeValue('mood_score', entry.mood_score)}</span>
                      {entry.notes && <span className="entry-list__note"><FileText size={14} aria-hidden="true" /> Note</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      )}
    </>
  )
}
