import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { format } from 'date-fns'
import { Users } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import {
  useAnnouncement,
  useAnnouncementStats,
  useMarkRead,
} from '../../hooks/useAnnouncements'
import { TopBar } from '../../components/layout/TopBar'
import { PriorityBadge } from '../../components/common/PriorityBadge'
import { ReadPercentageBar } from '../../components/announcements/ReadPercentageBar'
import { Card } from '../../components/ui/Card'

export default function AnnouncementDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { data: ann } = useAnnouncement(id)
  const { data: stats } = useAnnouncementStats(
    user?.role !== 'parent' ? id : undefined,
  )
  const markRead = useMarkRead()

  // Auto mark as read when the user opens the announcement
  useEffect(() => {
    if (id && ann && !ann.read_at) {
      markRead.mutate(id)
    }
  }, [id, ann?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!ann) {
    return (
      <>
        <TopBar title="Announcement" back />
        <div className="pt-14 px-4 py-8">
          <div className="h-6 w-48 animate-pulse rounded bg-gray-200" />
        </div>
      </>
    )
  }

  const publishedAt = ann.published_at ?? ann.created_at

  return (
    <>
      <TopBar title="Announcement" back />
      <div className="pt-14 px-4 py-4 flex flex-col gap-4">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <PriorityBadge priority={ann.priority} />
            <span className="text-xs text-gray-400">
              {format(new Date(publishedAt), 'd MMM yyyy, HH:mm')}
            </span>
          </div>
          <h1 className="text-xl font-bold text-gray-900 leading-snug">{ann.title}</h1>
        </div>

        {/* Body */}
        <Card className="p-4">
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{ann.body}</p>
        </Card>

        {/* Stats — teachers / admins only */}
        {stats && (
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Users size={16} className="text-gray-500" />
              <span className="text-sm font-semibold text-gray-700">Read receipts</span>
            </div>
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{stats.read_count} of {stats.total_recipients} parents read</span>
                <span>{stats.read_percentage.toFixed(0)}%</span>
              </div>
              <ReadPercentageBar percentage={stats.read_percentage} showLabel={false} />
            </div>
            {stats.breakdown.length > 1 && (
              <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-gray-100">
                {stats.breakdown.map((b) => (
                  <div key={b.target}>
                    <div className="flex justify-between text-xs text-gray-600 mb-0.5">
                      <span>{b.target}</span>
                      <span>{b.read}/{b.total}</span>
                    </div>
                    <ReadPercentageBar percentage={b.percentage} showLabel={false} />
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}
      </div>
    </>
  )
}
