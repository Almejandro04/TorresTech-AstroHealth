import { ArrowRight, CircleDashed } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description: string
  items: { label: string; description: string }[]
}

export function SectionPlaceholder({ icon: Icon, title, description, items }: Props) {
  return (
    <section className="workspace-panel" aria-label={title}>
      <div className="section-illustration" aria-hidden="true">
        <div className="illustration-orbit" />
        <Icon size={40} strokeWidth={1.35} />
        <span className="illustration-dot" />
      </div>
      <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest text-slate-500 uppercase">
        <CircleDashed size={14} aria-hidden="true" /> View in preparation
      </div>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">{title}</h2>
      <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-slate-500">{description}</p>
      <div className="feature-grid">
        {items.map((item) => (
          <div className="feature-note" key={item.label}>
            <span className="feature-marker" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-semibold text-slate-800">{item.label}</h3>
              <p className="mt-1 text-xs leading-6 text-slate-500">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="panel-footer">
        <p>Explore your mission workspace.</p>
        <Link to="/journal" className="text-link">Daily wellbeing <ArrowRight size={15} aria-hidden="true" /></Link>
      </div>
    </section>
  )
}
