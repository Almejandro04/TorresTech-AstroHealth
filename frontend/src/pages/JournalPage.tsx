import { BookOpen } from 'lucide-react'
import { SectionPlaceholder } from '../components/SectionPlaceholder'

export function JournalPage() {
  return <SectionPlaceholder icon={BookOpen} title="A moment to check in." description="The daily journal is being prepared. It will provide a simple place to record sleep, mood and notes, with the ability to correct an existing entry." items={[
    { label: 'Last night\u2019s sleep', description: 'Record the number of hours slept.' },
    { label: 'How you feel', description: 'Five clearly labeled mood options.' },
    { label: 'Your observations', description: 'Add notes and review daily entries.' },
  ]} />
}
