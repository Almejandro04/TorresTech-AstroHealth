import { useEffect, useRef } from 'react'
import { Bell, BookOpen, ChartNoAxesCombined, FlaskConical, LayoutDashboard, Orbit, RotateCcw, ShieldCheck } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useMissionData } from '../hooks/useMissionData'

const pages = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, subtitle: 'A clear view of your mission health.' },
  { path: '/analytics', label: 'Analytics', icon: ChartNoAxesCombined, subtitle: 'Explore observations across the mission.' },
  { path: '/alerts', label: 'Alerts', icon: Bell, subtitle: 'Understand changes and their context.' },
  { path: '/journal', label: 'Journal', icon: BookOpen, subtitle: 'Make space for your daily wellbeing.' },
]

const formatTime = (timestamp: string) => new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
}).format(new Date(timestamp)) + ' UTC'

export function AppShell() {
  const location = useLocation()
  const page = pages.find((candidate) => candidate.path === location.pathname)
  const heading = useRef<HTMLHeadingElement>(null)
  const { state, retry } = useMissionData()

  useEffect(() => {
    document.title = `${page?.label ?? 'Page not found'} · AstroHealth`
    heading.current?.focus({ preventScroll: true })
  }, [location.pathname, page?.label])

  const response = state.status === 'ready' ? state.response : null
  const summary = response?.data

  return (
    <div className="app-layout">
      <a className="skip-link" href="#main-content" onClick={(event) => {
        event.preventDefault()
        heading.current?.focus()
        heading.current?.scrollIntoView({ behavior: 'instant', block: 'start' })
      }}>Skip to content</a>

      <aside className="app-sidebar">
        <NavLink to="/dashboard" className="brand" aria-label="AstroHealth home">
          <span className="brand-icon"><Orbit size={25} strokeWidth={1.6} aria-hidden="true" /></span>
          <span>Astro<span className="font-normal text-teal-200">Health</span><span className="brand-caption">MISSION WELLBEING</span></span>
        </NavLink>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Primary navigation" className="primary-nav">
          {pages.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} className={({ isActive }) => `nav-item${isActive ? ' nav-item-active' : ''}`}>
              <Icon size={19} strokeWidth={1.7} aria-hidden="true" /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-mission">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-200"><span className="status-dot" /> FICTIONAL MISSION</div>
          <p className="mt-3 text-sm font-medium text-white">A little perspective.<br />A healthier mission.</p>
          <p className="mt-3 text-xs leading-6 text-slate-400">Built by TorresTech for NASA Space Apps Challenge 2026.</p>
        </div>
        <div className="sidebar-footer"><Orbit size={14} aria-hidden="true" /><span>TorresTech</span><span className="ml-auto">2026</span></div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <p className="text-xs text-slate-500"><span className="font-medium text-slate-800">Mission workspace</span><span className="mx-3 text-slate-300">/</span>{page?.label ?? 'Page not found'}</p>
          <span className="demo-badge"><FlaskConical size={13} aria-hidden="true" /> Synthetic demo</span>
        </header>

        <main id="main-content" className="main-content">
          <div className="page-heading">
            <div><p className="eyebrow">YOUR MISSION WORKSPACE</p><h1 id="page-title" tabIndex={-1} ref={heading}>{page?.label ?? 'Page not found'}</h1><p className="mt-2 text-sm leading-7 text-slate-500">{page?.subtitle ?? 'Find your way back to the mission.'}</p></div>
            <div className="profile-avatar" aria-hidden="true">{summary ? 'DA' : '—'}</div>
          </div>

          <section className="mission-strip" aria-label="Mission context" aria-busy={state.status === 'loading'}>
            {state.status === 'loading' && <p role="status" className="text-sm text-slate-500">Loading mission information...</p>}
            {state.status === 'error' && <div className="flex flex-wrap items-center gap-3"><p role="alert" className="text-sm text-slate-700">{state.message}</p><button type="button" className="text-link" onClick={retry}><RotateCcw size={14} aria-hidden="true" /> Try again</button></div>}
            {summary && <>
              <div className="mission-person"><span className="mission-label">ASTRONAUT</span><span className="mission-value">{summary.astronaut.name}</span><span className="text-xs text-slate-500">{summary.astronaut.astronaut_id} · Fictional profile</span></div>
              <div><span className="mission-label">MISSION DAY</span><span className="mission-value">{summary.mission_day === null ? 'No observations' : <>{String(summary.mission_day).padStart(2, '0')}<span className="text-sm font-normal text-slate-400"> / {summary.astronaut.planned_duration_days}</span></>}</span></div>
              <div className="mission-time"><span className="mission-label">MISSION VIEW AT</span><span className="text-sm font-medium text-slate-700">{response?.meta.as_of ? formatTime(response.meta.as_of) : 'No observations yet'}</span></div>
            </>}
          </section>

          <Outlet />

          <div className="prototype-note"><ShieldCheck size={16} aria-hidden="true" /><p>Synthetic observations · Monitoring prototype, not a validated medical diagnosis.</p></div>
        </main>
        <footer className="main-footer"><span>AstroHealth · TorresTech</span><span>Every observation needs context.</span></footer>
      </div>
    </div>
  )
}
