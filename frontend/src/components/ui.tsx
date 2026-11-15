import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'
import {
  CircleAlert,
  CircleCheck,
  CircleDashed,
  Info,
  LoaderCircle,
  OctagonAlert,
  RotateCcw,
  TriangleAlert,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { HealthDataError } from '../services'
import { SEVERITY_LABELS } from '../lib/metrics'
import { useMission } from '../hooks/MissionContext'
import type { AlertStatus, Severity } from '../types/health'

// ---------------------------------------------------------------------------------------------
// Tones. Every tone ships with its own icon and a text label: color never works alone.

export type Tone = 'info' | 'success' | 'warning' | 'critical' | 'neutral'

const TONE_ICON: Record<Tone, LucideIcon> = {
  info: Info,
  success: CircleCheck,
  warning: TriangleAlert,
  critical: OctagonAlert,
  neutral: CircleDashed,
}

interface CalloutProps {
  tone: Tone
  title: string
  children?: ReactNode
  actions?: ReactNode
  icon?: LucideIcon
  /** `alert` interrupts assistive technology (failures); `status` announces politely. */
  role?: 'alert' | 'status'
  compact?: boolean
}

export function Callout({ tone, title, children, actions, icon, role, compact = false }: CalloutProps) {
  const Icon = icon ?? TONE_ICON[tone]
  return (
    <div className={`callout callout--${tone}${compact ? ' callout--compact' : ''}`} role={role}>
      <Icon className="callout__icon" size={20} aria-hidden="true" />
      <div className="callout__body">
        <p className="callout__title">{title}</p>
        {children && <div className="callout__text">{children}</div>}
        {actions && <div className="callout__actions">{actions}</div>}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------------------------
// Badges

/** Shape, label, and weight change with the level; only "Critical" is a solid fill. */
const SEVERITY_ICON: Record<Severity, LucideIcon> = { info: Info, warning: TriangleAlert, critical: OctagonAlert }

export function SeverityBadge({ severity }: { severity: Severity }) {
  const Icon = SEVERITY_ICON[severity]
  return (
    <span className={`badge badge--severity-${severity}`}>
      <Icon size={14} aria-hidden="true" />
      <span className="visually-hidden">Attention level: </span>
      {SEVERITY_LABELS[severity]}
    </span>
  )
}

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  return (
    <span className={`badge badge--status-${status}`}>
      {status === 'active' ? <CircleAlert size={14} aria-hidden="true" /> : <CircleCheck size={14} aria-hidden="true" />}
      <span className="visually-hidden">Status: </span>
      {status === 'active' ? 'Active' : 'Resolved'}
    </span>
  )
}

export function Tag({ children, icon: Icon }: { children: ReactNode; icon?: LucideIcon }) {
  return (
    <span className="tag">
      {Icon && <Icon size={13} aria-hidden="true" />}
      {children}
    </span>
  )
}

// ---------------------------------------------------------------------------------------------
// Page structure

/** The route's single h1. It receives focus after navigation so keyboard users land on it. */
export function PageHeader({ title, lead, actions }: { title: string; lead?: ReactNode; actions?: ReactNode }) {
  const { astronaut, view, viewDay, isHistorical } = useMission()
  const summary = view.status === 'ready' ? view.data.data : null
  return (
    <header className="page-header">
      <div>
        <h1 id="page-title" tabIndex={-1}>{title}</h1>
        {astronaut && (
          <p className="page-header__context">
            <span>{astronaut.name}</span>
            <span className="mono">{astronaut.astronaut_id}</span>
            <span>
              {summary && viewDay !== null
                ? `${isHistorical ? 'Historical view' : 'Mission view'}: Day ${viewDay} of ${astronaut.planned_duration_days}`
                : summary
                  ? 'No observations yet'
                  : 'Loading mission view…'}
            </span>
          </p>
        )}
        {lead && <p className="page-header__lead">{lead}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  )
}

interface SectionProps {
  title: string
  note?: ReactNode
  actions?: ReactNode
  children: ReactNode
  busy?: boolean
  id?: string
}

/** A ruled block with its own heading: the flight-log replacement for a card. */
export function Section({ title, note, actions, children, busy = false, id }: SectionProps) {
  const headingId = useId()
  return (
    <section className="section" aria-labelledby={headingId} aria-busy={busy} id={id}>
      <div className="section__head">
        <h2 id={headingId}>{title}</h2>
        {note && <p className="section__note">{note}</p>}
        {actions && <div className="section__actions">{actions}</div>}
      </div>
      <div className={`section__body${busy ? ' is-refreshing' : ''}`}>{children}</div>
    </section>
  )
}

// ---------------------------------------------------------------------------------------------
// Data states

export function LoadingBlock({ label, rows = 3 }: { label: string; rows?: number }) {
  return (
    <div className="loading" role="status">
      <p className="loading__label">
        <LoaderCircle className="spin" size={16} aria-hidden="true" />
        {label}
      </p>
      <div className="loading__rows" aria-hidden="true">
        {Array.from({ length: rows }, (_, index) => <span key={index} className="skeleton" />)}
      </div>
    </div>
  )
}

interface ErrorCopy {
  title: string
  body: string
}

/** Plain-language recovery guidance by failure kind; codes and stack traces are never shown. */
export function describeError(error: HealthDataError, subject: string): ErrorCopy {
  switch (error.kind) {
    case 'network':
      return {
        title: `Could not load ${subject}`,
        body: 'The data source did not respond. Nothing is shown because the request did not complete, which is different from having no observations.',
      }
    case 'timeout':
      return { title: `Loading ${subject} took too long`, body: 'The data source did not answer in time. Try again.' }
    case 'not_found':
      return { title: 'Astronaut profile not found', body: 'The data source does not have this profile. Choose another profile from the mission bar.' }
    case 'validation':
      return { title: `The request for ${subject} was not accepted`, body: 'The selected day or period is outside the mission. Choose a different one.' }
    default:
      return { title: `Could not load ${subject}`, body: 'The data source reported a problem. Try again in a moment.' }
  }
}

export function ErrorState({ error, subject, onRetry }: { error: HealthDataError; subject: string; onRetry: () => void }) {
  const copy = describeError(error, subject)
  return (
    <Callout
      tone="critical"
      title={copy.title}
      role="alert"
      icon={CircleAlert}
      actions={
        <button type="button" className="button button--secondary" onClick={onRetry}>
          <RotateCcw size={16} aria-hidden="true" /> Try again
        </button>
      }
    >
      <p>{copy.body}</p>
    </Callout>
  )
}

// ---------------------------------------------------------------------------------------------
// Controls

interface SegmentedOption<T extends string> {
  value: T
  label: string
  detail?: string
}

interface SegmentedProps<T extends string> {
  legend: string
  name: string
  value: T
  options: SegmentedOption<T>[]
  onChange: (value: T) => void
}

/** Native radio group: arrow keys move between options and the choice is announced. */
export function Segmented<T extends string>({ legend, name, value, options, onChange }: SegmentedProps<T>) {
  return (
    <fieldset className="segmented">
      <legend className="field__label">{legend}</legend>
      <div className="segmented__options">
        {options.map((option) => (
          <label key={option.value} className="segmented__option">
            <input type="radio" name={name} value={option.value} checked={option.value === value} onChange={() => onChange(option.value)} />
            <span>
              {option.label}
              {option.detail && <span className="segmented__detail">{option.detail}</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

interface DialogProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}

/** Native modal dialog: focus is trapped, Escape closes it, and focus returns to the opener. */
export function Dialog({ open, title, onClose, children, footer, wide = false }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className={`dialog${wide ? ' dialog--wide' : ''}`}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
    >
      {open && (
        <div className="dialog__panel">
          <h2 id={titleId} className="dialog__title">{title}</h2>
          <div className="dialog__body">{children}</div>
          {footer && <div className="dialog__footer">{footer}</div>}
        </div>
      )}
    </dialog>
  )
}
