import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Announcement, AnnouncementStats, Channel } from '../types'

export function useChannels() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => api.get<Channel[]>('/channels'),
  })
}

export function useAnnouncements(channelId: string | undefined, priority?: string) {
  const params = new URLSearchParams()
  if (priority) params.set('priority', priority)
  const qs = params.toString() ? `?${params}` : ''

  return useQuery({
    queryKey: ['announcements', channelId, priority],
    queryFn: () =>
      api.get<Announcement[]>(`/channels/${channelId}/announcements${qs}`),
    enabled: !!channelId,
  })
}

export function useAllAnnouncements(channelIds: string[]) {
  const queryClient = useQueryClient()
  // Flatten announcements from all channels, deduped by id, sorted by date
  const results = channelIds.map((id) =>
    queryClient.getQueryData<Announcement[]>(['announcements', id]) ?? [],
  )
  const all = results
    .flat()
    .sort((a, b) => {
      const ta = a.published_at ?? a.created_at
      const tb = b.published_at ?? b.created_at
      return new Date(tb).getTime() - new Date(ta).getTime()
    })
  const seen = new Set<string>()
  return all.filter((a) => {
    if (seen.has(a.id)) return false
    seen.add(a.id)
    return true
  })
}

export function useAnnouncement(id: string | undefined) {
  return useQuery({
    queryKey: ['announcement', id],
    queryFn: () => api.get<Announcement>(`/announcements/${id}`),
    enabled: !!id,
  })
}

export function useAnnouncementStats(id: string | undefined) {
  return useQuery({
    queryKey: ['announcement-stats', id],
    queryFn: () => api.get<AnnouncementStats>(`/announcements/${id}/stats`),
    enabled: !!id,
  })
}

export function useMarkRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/announcements/${id}/read`),
    onSuccess: (_data, id) => {
      // Optimistically update the read_at on cached announcement
      queryClient.setQueryData<Announcement>(['announcement', id], (old) =>
        old ? { ...old, read_at: new Date().toISOString() } : old,
      )
      // Invalidate list queries so the unread badge updates
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
    },
  })
}

export function useCreateAnnouncement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      channel_id: string
      title: string
      body: string
      priority: string
      is_pinned: boolean
      send_whatsapp: boolean
    }) => api.post<Announcement>('/announcements', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
    },
  })
}
