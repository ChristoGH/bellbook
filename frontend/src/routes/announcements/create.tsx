import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChannels, useCreateAnnouncement } from '../../hooks/useAnnouncements'
import { TopBar } from '../../components/layout/TopBar'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import type { Priority } from '../../types'

export default function CreateAnnouncementPage() {
  const navigate = useNavigate()
  const { data: channels = [] } = useChannels()
  const create = useCreateAnnouncement()

  const [channelId, setChannelId] = useState(channels[0]?.id ?? '')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [priority, setPriority] = useState<Priority>('normal')
  const [isPinned, setIsPinned] = useState(false)
  const [sendWhatsapp, setSendWhatsapp] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit() {
    setError('')
    if (!channelId) { setError('Please select a channel'); return }
    if (!title.trim()) { setError('Title is required'); return }
    if (!body.trim()) { setError('Body is required'); return }
    try {
      await create.mutateAsync({ channel_id: channelId, title, body, priority, is_pinned: isPinned, send_whatsapp: sendWhatsapp })
      navigate(-1)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to post announcement')
    }
  }

  return (
    <>
      <TopBar title="New announcement" back />
      <div className="pt-14 px-4 py-4 flex flex-col gap-4">
        {/* Channel */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Channel</label>
          <select
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            className="h-11 w-full rounded-xl border border-gray-300 px-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          >
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>{ch.name}</option>
            ))}
          </select>
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
          <div className="flex gap-2">
            {(['info', 'normal', 'urgent'] as Priority[]).map((p) => (
              <button
                key={p}
                onClick={() => setPriority(p)}
                className={`flex-1 rounded-xl py-2 text-sm font-medium capitalize transition-colors border ${
                  priority === p
                    ? p === 'urgent'
                      ? 'bg-red-50 border-red-400 text-red-700'
                      : p === 'normal'
                      ? 'bg-indigo-50 border-indigo-400 text-indigo-700'
                      : 'bg-gray-100 border-gray-400 text-gray-700'
                    : 'border-gray-200 text-gray-500 hover:bg-gray-50'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <Input
          label="Title"
          placeholder="Grade 4 sports day reminder"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your announcement here..."
            rows={5}
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100 resize-none"
          />
        </div>

        {/* Options */}
        <div className="flex flex-col gap-2">
          {[
            { label: 'Pin to top', value: isPinned, set: setIsPinned },
            { label: 'Also send via WhatsApp', value: sendWhatsapp, set: setSendWhatsapp },
          ].map(({ label, value, set }) => (
            <label key={label} className="flex items-center justify-between rounded-xl bg-white border border-gray-100 px-4 py-3">
              <span className="text-sm font-medium text-gray-700">{label}</span>
              <button
                onClick={() => set(!value)}
                className={`relative h-6 w-11 rounded-full transition-colors ${value ? 'bg-indigo-600' : 'bg-gray-300'}`}
              >
                <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
            </label>
          ))}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button onClick={handleSubmit} loading={create.isPending} size="lg" className="w-full">
          Post announcement
        </Button>
      </div>
    </>
  )
}
