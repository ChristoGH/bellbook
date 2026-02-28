import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../lib/auth'
import type { TokenResponse } from '../types'

const INITIAL_RETRY_DELAY = 3_000
const MAX_RETRY_DELAY = 30_000

async function tryRefreshToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) return null
    const data: TokenResponse = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    return null
  }
}

type SSEEvent = { type: string; [key: string]: unknown }

function handleEvent(data: SSEEvent, invalidate: (key: unknown[]) => void) {
  switch (data.type) {
    case 'announcement.new':
      invalidate(['announcements'])
      invalidate(['channels'])
      break
    case 'message.new':
      invalidate(['conversations'])
      if (data.conversation_id) invalidate(['messages', data.conversation_id])
      break
    case 'connected':
      break
  }
}

/** Opens an SSE connection and keeps it alive for the session lifetime.
 *  Handles token refresh and exponential-backoff reconnection automatically.
 *  Must only be mounted inside an authenticated route. */
export function useSSE() {
  const queryClient = useQueryClient()
  const esRef = useRef<EventSource | null>(null)
  const retryDelayRef = useRef(INITIAL_RETRY_DELAY)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const invalidate = useCallback(
    (key: unknown[]) => queryClient.invalidateQueries({ queryKey: key }),
    [queryClient],
  )

  const connect = useCallback(async () => {
    if (!mountedRef.current) return
    let token = getAccessToken()
    if (!token) return

    const url = `/api/events/stream?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      retryDelayRef.current = INITIAL_RETRY_DELAY // reset backoff on success
    }

    es.onmessage = (ev) => {
      try {
        const data: SSEEvent = JSON.parse(ev.data)
        handleEvent(data, invalidate)
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = async () => {
      es.close()
      esRef.current = null
      if (!mountedRef.current) return

      // Attempt token refresh — the 15-min access token may have expired
      token = await tryRefreshToken()
      if (!token) {
        clearTokens()
        window.location.href = '/login'
        return
      }

      // Exponential backoff reconnect
      const delay = retryDelayRef.current
      retryDelayRef.current = Math.min(delay * 2, MAX_RETRY_DELAY)
      retryTimerRef.current = setTimeout(connect, delay)
    }
  }, [invalidate])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      esRef.current?.close()
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
    }
  }, [connect])
}
