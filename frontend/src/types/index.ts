export type Role = 'super_admin' | 'school_admin' | 'teacher' | 'parent'

export interface User {
  id: string
  school_id: string | null
  email: string | null
  phone: string | null
  first_name: string
  last_name: string
  role: Role
  preferred_lang: string
  avatar_url: string | null
  is_active: boolean
}

export type Priority = 'urgent' | 'normal' | 'info'
export type ChannelType = 'school' | 'grade' | 'class' | 'custom'

export interface Channel {
  id: string
  school_id: string
  name: string
  type: ChannelType
  description: string | null
  grade_id: string | null
  class_id: string | null
  is_active: boolean
  created_at: string
}

export interface Announcement {
  id: string
  channel_id: string
  author_id: string
  title: string
  body: string
  priority: Priority
  is_pinned: boolean
  send_whatsapp: boolean
  send_sms: boolean
  published_at: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
  read_at: string | null
}

export interface AnnouncementRead {
  user_id: string
  first_name: string
  last_name: string
  read_at: string
}

export interface ClassBreakdown {
  target: string
  total: number
  read: number
  percentage: number
}

export interface AnnouncementStats {
  announcement_id: string
  total_recipients: number
  read_count: number
  read_percentage: number
  unread_count: number
  breakdown: ClassBreakdown[]
  last_read_at: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// ---------------------------------------------------------------------------
// Messaging
// ---------------------------------------------------------------------------

export interface MessageItem {
  id: string
  conversation_id: string
  sender_id: string
  body: string
  is_system: boolean
  created_at: string
}

export interface Participant {
  user_id: string
  first_name: string
  last_name: string
  role: Role
  avatar_url: string | null
  is_muted: boolean
  is_blocked: boolean
}

export interface Conversation {
  id: string
  school_id: string
  subject: string | null
  learner_id: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
  participants: Participant[]
  last_message: MessageItem | null
  unread_count: number
}
