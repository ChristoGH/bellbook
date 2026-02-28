import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Conversation, MessageItem } from '../types'

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export function useConversations() {
  return useQuery<Conversation[]>({
    queryKey: ['conversations'],
    queryFn: () => api.get<Conversation[]>('/api/conversations'),
  })
}

export function useCreateConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      learner_id: string
      participant_id: string
      subject?: string
    }) => api.post<Conversation>('/api/conversations', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversations'] }),
  })
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export function useMessages(conversationId: string) {
  return useQuery<MessageItem[]>({
    queryKey: ['messages', conversationId],
    queryFn: () =>
      api.get<MessageItem[]>(`/api/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
  })
}

export function useSendMessage(conversationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: string) =>
      api.post<MessageItem>(`/api/conversations/${conversationId}/messages`, {
        body,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['messages', conversationId] })
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

// ---------------------------------------------------------------------------
// Mark read
// ---------------------------------------------------------------------------

export function useMarkConversationRead(conversationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api.put<void>(`/api/conversations/${conversationId}/read`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

// ---------------------------------------------------------------------------
// Teacher / admin actions
// ---------------------------------------------------------------------------

export function useMuteConversation(conversationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (muted: boolean) =>
      api.put<void>(`/api/conversations/${conversationId}/mute`, { muted }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      qc.invalidateQueries({ queryKey: ['messages', conversationId] })
    },
  })
}

export function useBlockParticipant(conversationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      userId,
      blocked,
    }: {
      userId: string
      blocked: boolean
    }) =>
      api.put<void>(`/api/conversations/${conversationId}/block`, {
        user_id: userId,
        blocked,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      qc.invalidateQueries({ queryKey: ['messages', conversationId] })
    },
  })
}
