import { LayoutDashboard } from 'lucide-react'
import { SectionPlaceholder } from '../components/SectionPlaceholder'

export function DashboardPage() {
  return <SectionPlaceholder icon={LayoutDashboard} title="Your mission, in focus." description="This overview is being prepared. It will bring your latest observations and daily wellbeing together, with clear context for every value." items={[
    { label: 'Vital observations', description: 'Heart rate, oxygen and breathing.' },
    { label: 'Daily wellbeing', description: 'Sleep, mood and personal notes.' },
    { label: 'Attention and context', description: 'Understandable monitoring alerts.' },
  ]} />
}
