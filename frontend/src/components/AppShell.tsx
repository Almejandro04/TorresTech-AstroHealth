import { useEffect, useRef, useState } from 'react'
import { ChartLine, LayoutDashboard, Moon, NotebookPen, Sun, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { MissionProvider, useMission } from '../hooks/MissionContext'
import { useTheme } from '../hooks/useTheme'
import { BrandMark } from './BrandMark'
import { DemoScenarios } from './DemoScenarios'
import { MissionBar } from './MissionBar'

interface Destination {
  path: string
  label: string
  icon: LucideIcon
}

/** Four destinations, always in this order, in the masthead and in the mobile tab bar. */
const DESTINATIONS: Destination[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/analytics', label: 'Analytics', icon: ChartLine },
  { path: '/alerts', label: 'Alerts', icon: TriangleAlert },
  { path: '/journal', label: 'Journal', icon: NotebookPen },
]

function PrimaryNav({ variant }: { variant: 'masthead' | 'tabbar' }) {
  const { view, linkTo } = useMission()
  const summary = view.status === 'ready' ? view.data.data.alert_summary : null
  // A count is shown only when an evaluation actually ran; otherwise there is nothing to count.
  const activeAlerts = summary?.evaluation_status === 'available' ? summary.active_count ?? 0 : 0

  return (
    <nav className={`nav nav--${variant}`} aria-label={variant === 'masthead' ? 'Primary' : 'Primary, bottom bar'}>
      <ul>
        {DESTINATIONS.map(({ path, label, icon: Icon }) => (
          <li key={path}>
            <NavLink to={linkTo(path)} className={({ isActive }) => `nav__link${isActive ? ' is-active' : ''}`}>
              <Icon size={variant === 'tabbar' ? 22 : 18} aria-hidden="true" />
              <span>{label}</span>
              {path === '/alerts' && activeAlerts > 0 && (
                <span className="nav__count">
                  {activeAlerts}
                  <span className="visually-hidden"> active {activeAlerts === 1 ? 'alert' : 'alerts'}</span>
                </span>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

function Shell() {
  const location = useLocation()
  const { linkTo } = useMission()
  const { theme, toggle } = useTheme()
  const [demoOpen, setDemoOpen] = useState(false)
  const firstRender = useRef(true)
  const section = location.pathname.split('/')[1] ?? ''
  const destination = DESTINATIONS.find((candidate) => candidate.path === `/${section}`)

  // After moving to another view, name it in the tab title and put focus on its heading.
  useEffect(() => {
    document.title = `${destination?.label ?? 'Page not found'} · AstroHealth`
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    document.getElementById('page-title')?.focus({ preventScroll: true })
    window.scrollTo(0, 0)
  }, [section, destination?.label])

  return (
    <div className="app">
      <a className="skip-link" href="#main" onClick={(event) => {
        event.preventDefault()
        document.getElementById('page-title')?.focus()
      }}>Skip to main content</a>

      <header className="masthead">
        <div className="masthead__inner">
          <Link to={linkTo('/dashboard')} className="brand" aria-label="AstroHealth, go to Dashboard">
            <BrandMark />
            <span className="brand__name">AstroHealth</span>
          </Link>
          <PrimaryNav variant="masthead" />
          <button
            type="button"
            className="masthead__button"
            onClick={toggle}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          >
            {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
            <span aria-hidden="true">{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </header>

      <MissionBar onOpenDemo={() => setDemoOpen(true)} />

      <main id="main" className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="footer__inner">
          <p>
            <strong>Synthetic observations.</strong> AstroHealth is a monitoring prototype with experimental
            interpretations. It is not a validated medical diagnosis.
          </p>
          <p className="footer__credit">
            AstroHealth by TorresTech · NASA Space Apps Challenge 2026 · Not affiliated with or endorsed by NASA.
          </p>
        </div>
      </footer>

      <PrimaryNav variant="tabbar" />
      <DemoScenarios open={demoOpen} onClose={() => setDemoOpen(false)} />
    </div>
  )
}

export function AppShell() {
  return (
    <MissionProvider>
      <Shell />
    </MissionProvider>
  )
}
