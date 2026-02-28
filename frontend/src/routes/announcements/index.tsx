import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useChannels, useAnnouncements } from '../../hooks/useAnnouncements'
import { TopBar } from '../../components/layout/TopBar'
import { AnnouncementCard } from '../../components/announcements/AnnouncementCard'
import { EmptyState } from '../../components/common/EmptyState'
import { Button } from '../../components/ui/Button'
import type { Priority } from '../../types'

const PRIORITIES: { value: Priority | 'all'; label: string }[] = [
  { value: 'all',    label: 'All' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'normal', label: 'Notice' },
  { value: 'info',   label: 'Info' },
]

export default function AnnouncementsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: channels = [] } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | undefined>(channels[0]?.id)
  const [priority, setPriority] = useState<Priority | 'all'>('all')

  const { data: announcements = [], isLoading } = useAnnouncements(
    activeChannel ?? channels[0]?.id,
    priority === 'all' ? undefined : priority,
  )

  const canCreate = user?.role === 'teacher' || user?.role === 'school_admin'
  const channelId = activeChannel ?? channels[0]?.id

  return (
    <>
      <TopBar
        title="Announcements"
        action={
          canCreate ? (
            <Button size="sm" onClick={() => navigate('/announcements/create')}>
              <Plus size={16} /> Post
            </Button>
          ) : null
        }
      />

      <div className="pt-14 flex flex-col">
        {/* Channel tabs */}
        {channels.length > 0 && (
          <div className="flex gap-2 overflow-x-auto px-4 py-2 border-b border-gray-100 bg-white">
            {channels.map((ch) => (
              <button
                key={ch.id}
                onClick={() => setActiveChannel(ch.id)}
                className={`flex-shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  (activeChannel ?? channels[0]?.id) === ch.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {ch.name}
              </button>
            ))}
          </div>
        )}

        {/* Priority filter */}
        <div className="flex gap-2 overflow-x-auto px-4 py-2 bg-white border-b border-gray-100">
          {PRIORITIES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setPriority(value)}
              className={`flex-shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                priority === value
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3 px-4 py-4">
          {isLoading && [1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-gray-200" />
          ))}

          {!isLoading && announcements.length === 0 && (
            <EmptyState
              title="Nothing here"
              description={priority !== 'all' ? 'Try changing the priority filter.' : 'No announcements posted yet.'}
            />
          )}

          {announcements.map((ann) => (
            <AnnouncementCard
              key={ann.id}
              announcement={ann}
              channelName={channels.find((c) => c.id === ann.channel_id)?.name}
            />
          ))}
        </div>
      </div>
    </>
  )
}
