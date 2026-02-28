import { MessageSquare } from 'lucide-react'
import { useConversations } from '../../hooks/useConversations'
import { useAuth } from '../../hooks/useAuth'
import { TopBar } from '../../components/layout/TopBar'
import { EmptyState } from '../../components/common/EmptyState'
import { ConversationList } from '../../components/messages/ConversationList'

export default function MessagesPage() {
  const { user } = useAuth()
  const { data: conversations = [], isLoading } = useConversations()

  return (
    <>
      <TopBar title="Messages" />
      <div className="pt-14">
        {isLoading ? (
          <div className="flex justify-center pt-16">
            <div className="h-7 w-7 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState
            icon={<MessageSquare size={48} />}
            title="No messages yet"
            description="Conversations between parents and teachers will appear here."
          />
        ) : (
          <ConversationList
            conversations={conversations}
            currentUserId={user?.id ?? ''}
          />
        )}
      </div>
    </>
  )
}
