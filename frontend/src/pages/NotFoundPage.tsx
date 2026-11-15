import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useMission } from '../hooks/MissionContext'

export function NotFoundPage() {
  const { linkTo } = useMission()
  return (
    <header className="page-header">
      <div>
        <h1 id="page-title" tabIndex={-1}>Page not found</h1>
        <p className="page-header__lead">
          This address does not match a view. AstroHealth has four: Dashboard, Analytics, Alerts, and Journal.
        </p>
        <Link to={linkTo('/dashboard')} className="button button--primary">
          <ArrowLeft size={16} aria-hidden="true" /> Go to Dashboard
        </Link>
      </div>
    </header>
  )
}
