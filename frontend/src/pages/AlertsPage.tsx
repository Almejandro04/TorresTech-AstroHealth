import { Bell } from 'lucide-react'
import { SectionPlaceholder } from '../components/SectionPlaceholder'

export function AlertsPage() {
  return <SectionPlaceholder icon={Bell} title="Understand what needs attention." description="The alert view is being prepared. It will explain observed changes and the supporting evidence, without presenting them as medical diagnoses." items={[
    { label: 'Clear attention levels', description: 'Readable labels alongside visual cues.' },
    { label: 'Explainable observations', description: 'See the reason behind an alert.' },
    { label: 'Analysis availability', description: 'Know when more observations are needed.' },
  ]} />
}
