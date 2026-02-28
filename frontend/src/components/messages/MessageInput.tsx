import { Send } from 'lucide-react'
import { useState } from 'react'

interface Props {
  onSend: (body: string) => void
  disabled?: boolean
  loading?: boolean
}

export function MessageInput({ onSend, disabled = false, loading = false }: Props) {
  const [value, setValue] = useState('')

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || disabled || loading) return
    onSend(trimmed)
    setValue('')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-end gap-2 border-t border-gray-100 bg-white px-3 py-3 pb-safe-bottom">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message…"
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm leading-relaxed focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:opacity-50"
        style={{ maxHeight: '120px', overflowY: 'auto' }}
      />
      <button
        onClick={handleSend}
        disabled={!value.trim() || disabled || loading}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:opacity-40"
        aria-label="Send message"
      >
        {loading ? (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
        ) : (
          <Send size={18} />
        )}
      </button>
    </div>
  )
}
