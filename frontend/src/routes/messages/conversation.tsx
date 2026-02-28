import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import {
  useMessages,
  useMarkConversationRead,
  useSendMessage,
  useMuteConversation,
  useBlockParticipant,
} from '../../hooks/useConversations'
import { useAuth } from '../../hooks/useAuth'
import { TopBar } from '../../components/layout/TopBar'
import { ChatBubble } from '../../components/messages/ChatBubble'
import { MessageInput } from '../../components/messages/MessageInput'

export default function ConversationPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { user } = useAuth()
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: messages = [], isLoading } = useMessages(id)
  const send = useSendMessage(id)
  const markRead = useMarkConversationRead(id)
  const mute = useMuteConversation(id)
  const block = useBlockParticipant(id)

  // Mark read on mount and when new messages arrive
  useEffect(() => {
    if (messages.length > 0) {
      markRead.mutate()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length])

  // Scroll to bottom when messages load or new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const isBlocked = false // TODO: derive from conversation participants if needed

  return (
    <div className="flex flex-col h-dvh">
      <TopBar title="Conversation" back />

      {/* Message list */}
      <div className="flex-1 overflow-y-auto pt-14 pb-2">
        {isLoading ? (
          <div className="flex justify-center pt-16">
            <div className="h-7 w-7 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : messages.length === 0 ? (
          <p className="text-center text-sm text-gray-400 pt-16">
            No messages yet — say hello!
          </p>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatBubble
                key={msg.id}
                message={msg}
                isOwn={msg.sender_id === user?.id}
              />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <MessageInput
        onSend={(body) => send.mutate(body)}
        disabled={isBlocked || send.isPending}
        loading={send.isPending}
      />
    </div>
  )
}
