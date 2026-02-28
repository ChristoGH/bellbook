import { format } from 'date-fns'
import type { MessageItem } from '../../types'

interface Props {
  message: MessageItem
  isOwn: boolean
}

export function ChatBubble({ message, isOwn }: Props) {
  const time = format(new Date(message.created_at), 'HH:mm')

  // System messages (mute / block notices) render centered in gray italics
  if (message.is_system) {
    return (
      <div className="flex justify-center px-4 py-1">
        <p className="text-xs italic text-gray-400 text-center max-w-xs">
          {message.body}
        </p>
      </div>
    )
  }

  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} px-4 py-1`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm ${
          isOwn
            ? 'rounded-br-sm bg-indigo-600 text-white'
            : 'rounded-bl-sm bg-white text-gray-900'
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.body}
        </p>
        <p
          className={`mt-0.5 text-right text-[10px] ${
            isOwn ? 'text-indigo-200' : 'text-gray-400'
          }`}
        >
          {time}
        </p>
      </div>
    </div>
  )
}
