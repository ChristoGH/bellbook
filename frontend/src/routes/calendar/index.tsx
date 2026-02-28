import { CalendarDays } from 'lucide-react'
import { TopBar } from '../../components/layout/TopBar'
import { EmptyState } from '../../components/common/EmptyState'

// Full implementation in Prompt 5 (Supporting Features)
export default function CalendarPage() {
  return (
    <>
      <TopBar title="Calendar" />
      <div className="pt-14">
        <EmptyState
          icon={<CalendarDays size={48} />}
          title="Calendar coming soon"
          description="School events, term dates and exam schedules will appear here."
        />
      </div>
    </>
  )
}
