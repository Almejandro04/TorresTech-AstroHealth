import { ChartNoAxesCombined } from 'lucide-react'
import { SectionPlaceholder } from '../components/SectionPlaceholder'

export function AnalyticsPage() {
  return <SectionPlaceholder icon={ChartNoAxesCombined} title="See the story over time." description="The analytics view is being prepared. Observation histories and individual references will help you explore patterns across the mission." items={[
    { label: 'Observation history', description: 'Follow changes over mission days.' },
    { label: 'Individual references', description: 'Keep comparisons in context.' },
    { label: 'Honest data gaps', description: 'See when observations are missing.' },
  ]} />
}
