import { Component, useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { CircleAlert } from 'lucide-react'
import { BrandMark } from './BrandMark'

// This module must not import services/config or the router: it recovers failures
// in those modules before the main application has finished loading.
function RecoveryFrame({ children }: { children: ReactNode }) {
  return <div className="app">
    <header className="masthead"><div className="masthead__inner">
      <div className="brand"><BrandMark /><span className="brand__name">AstroHealth</span></div>
    </div></header>
    <main className="main">{children}</main>
  </div>
}

export function ApplicationLoading() {
  return <RecoveryFrame><p role="status">Loading Flight Log…</p></RecoveryFrame>
}

export function ApplicationError({ startup = false }: { startup?: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null)
  const title = startup ? 'Flight Log could not start' : 'This view could not be displayed'
  useEffect(() => {
    document.title = 'Unable to load · AstroHealth'
    heading.current?.focus()
  }, [])
  return <RecoveryFrame>
    <header className="page-header"><div><h1 ref={heading} tabIndex={-1}>{title}</h1></div></header>
    <div className="callout callout--critical" role="alert">
      <CircleAlert className="callout__icon" size={20} aria-hidden="true" />
      <div className="callout__body">
        <p className="callout__title">Reload to try again</p>
        <div className="callout__text"><p>{startup
          ? 'The application or its connection settings could not be loaded. If reloading does not help, ask the project maintainer to review the setup.'
          : 'The view encountered an unexpected error. Reloading may discard unsaved journal changes.'}</p></div>
        <div className="callout__actions"><button type="button" className="button button--secondary" onClick={() => window.location.reload()}>Reload Flight Log</button></div>
      </div>
    </div>
  </RecoveryFrame>
}

export class ApplicationBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { console.error('Flight Log could not display this view.') }
  render() { return this.state.failed ? <ApplicationError /> : this.props.children }
}
