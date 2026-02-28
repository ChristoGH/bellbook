import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Pin, CheckCircle } from 'lucide-react'
import { Card } from '../ui/Card'
import { PriorityBadge } from '../common/PriorityBadge'
import type { Announcement } from '../../types'

interface AnnouncementCardProps {
  announcement: Announcement
  channelName?: string
}

export function AnnouncementCard({ announcement, channelName }: AnnouncementCardProps) {
  const navigate = useNavigate()
  const isRead = !!announcement.read_at
  const publishedAt = announcement.published_at ?? announcement.created_at

  return (
    <Card
      onClick={() => navigate(`/announcements/${announcement.id}`)}
      className="p-4"
    >
      <div className="flex items-start gap-3">
        {/* Unread dot */}
        <div className="mt-1 flex-shrink-0">
          {isRead
            ? <CheckCircle size={16} className="text-green-500" />
            : <div className="h-2.5 w-2.5 rounded-full bg-indigo-500 mt-0.5" />
          }
        </div>

        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <PriorityBadge priority={announcement.priority} />
            {announcement.is_pinned && (
              <span className="flex items-center gap-0.5 text-xs text-gray-500">
                <Pin size={11} /> Pinned
              </span>
            )}
            {channelName && (
              <span className="text-xs text-gray-400">{channelName}</span>
            )}
          </div>

          {/* Title */}
          <h3 className={`mt-1 text-sm font-semibold leading-snug ${isRead ? 'text-gray-600' : 'text-gray-900'}`}>
            {announcement.title}
          </h3>

          {/* Body preview */}
          <p className="mt-0.5 text-xs text-gray-500 line-clamp-2 leading-relaxed">
            {announcement.body}
          </p>

          {/* Footer */}
          <p className="mt-1.5 text-[11px] text-gray-400">
            {formatDistanceToNow(new Date(publishedAt), { addSuffix: true })}
          </p>
        </div>
      </div>
    </Card>
  )
}
