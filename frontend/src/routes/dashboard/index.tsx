import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Plus } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useChannels, useAnnouncements } from '../../hooks/useAnnouncements'
import { TopBar } from '../../components/layout/TopBar'
import { AnnouncementCard } from '../../components/announcements/AnnouncementCard'
import { EmptyState } from '../../components/common/EmptyState'
import { Button } from '../../components/ui/Button'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: channels = [] } = useChannels()

  // Use the first available channel as the default feed
  // (a "unified feed" endpoint can be added later)
  const primaryChannel = channels[0]
  const { data: announcements = [], isLoading } = useAnnouncements(primaryChannel?.id)

  const canCreate = user?.role === 'teacher' || user?.role === 'school_admin'

  return (
    <>
      <TopBar
        title={`Hi, ${user?.first_name ?? ''}!`}
        action={
          canCreate ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/announcements/create')}
            >
              <Plus size={16} />
              Post
            </Button>
          ) : null
        }
      />

      <div className="pt-14 px-4 py-4 flex flex-col gap-3">
        {channels.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {channels.map((ch) => (
              <button
                key={ch.id}
                onClick={() => navigate('/announcements')}
                className="flex-shrink-0 rounded-full bg-white border border-gray-200 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
              >
                {ch.name}
              </button>
            ))}
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl bg-gray-200" />
            ))}
          </div>
        )}

        {!isLoading && announcements.length === 0 && (
          <EmptyState
            icon={<Bell size={48} />}
            title="No announcements yet"
            description="New notices from your school will appear here."
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
    </>
  )
}
