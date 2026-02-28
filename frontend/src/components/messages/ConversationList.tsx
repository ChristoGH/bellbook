import { formatDistanceToNow } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import type { Conversation } from '../../types'
import { Avatar } from '../ui/Avatar'

interface Props {
  conversations: Conversation[]
  currentUserId: string
}

export function ConversationList({ conversations, currentUserId }: Props) {
  const navigate = useNavigate()

  if (conversations.length === 0) {
    return (
      <p className="text-center text-sm text-gray-400 py-10">
        No conversations yet
      </p>
    )
  }

  return (
    <ul className="divide-y divide-gray-100">
      {conversations.map((conv) => {
        const other = conv.participants.find((p) => p.user_id !== currentUserId)
        const name = other
          ? `${other.first_name} ${other.last_name}`
          : 'Conversation'
        const preview = conv.last_message?.body ?? 'No messages yet'
        const time = conv.last_message
          ? formatDistanceToNow(new Date(conv.last_message.created_at), {
              addSuffix: true,
            })
          : ''
        const isSystem = conv.last_message?.is_system ?? false

        return (
          <li key={conv.id}>
            <button
              onClick={() => navigate(`/messages/${conv.id}`)}
              className="flex w-full items-center gap-3 px-4 py-3.5 hover:bg-gray-50 transition-colors text-left"
            >
              <div className="relative shrink-0">
                <Avatar name={name} src={other?.avatar_url ?? null} size="md" />
                {conv.unread_count > 0 && (
                  <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">
                    {conv.unread_count > 9 ? '9+' : conv.unread_count}
                  </span>
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {name}
                  </p>
                  {time && (
                    <span className="shrink-0 text-xs text-gray-400">{time}</span>
                  )}
                </div>
                {conv.subject && (
                  <p className="truncate text-xs text-indigo-600 font-medium">
                    {conv.subject}
                  </p>
                )}
                <p
                  className={`truncate text-sm ${
                    isSystem
                      ? 'italic text-gray-400'
                      : conv.unread_count > 0
                      ? 'font-medium text-gray-800'
                      : 'text-gray-500'
                  }`}
                >
                  {preview}
                </p>
              </div>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
