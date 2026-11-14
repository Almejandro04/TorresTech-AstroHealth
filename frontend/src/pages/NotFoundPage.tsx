import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return <section className="workspace-panel"><p className="eyebrow">Page not found</p><h2 className="mt-3 text-2xl font-semibold">Let's get back on course.</h2><p className="mt-3 text-sm text-slate-500">This page does not exist in the mission workspace.</p><Link to="/dashboard" className="primary-link mt-6"><ArrowLeft size={16} aria-hidden="true" /> Back to dashboard</Link></section>
}
