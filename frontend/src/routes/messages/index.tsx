import { MessageSquare } from 'lucide-react'
import { TopBar } from '../../components/layout/TopBar'
import { EmptyState } from '../../components/common/EmptyState'

// Full implementation in Prompt 5 (Messaging)
export default function MessagesPage() {
  return (
    <>
      <TopBar title="Messages" />
      <div className="pt-14">
        <EmptyState
          icon={<MessageSquare size={48} />}
          title="Messages coming soon"
          description="Direct messaging between parents and teachers will be available shortly."
        />
      </div>
    </>
  )
}
