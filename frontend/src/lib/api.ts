import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './auth'
import type { TokenResponse } from '../types'

const BASE = '/api'

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const makeHeaders = (token: string | null): HeadersInit => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers ?? {}),
  })

  let token = getAccessToken()
  let res = await fetch(`${BASE}${path}`, { ...init, headers: makeHeaders(token) })

  if (res.status === 401) {
    token = await refreshAccessToken()
    if (!token) {
      clearTokens()
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    res = await fetch(`${BASE}${path}`, { ...init, headers: makeHeaders(token) })
  }

  if (res.status === 204) return undefined as T

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(body.detail ?? 'Request failed')
  }

  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: 'GET', ...init }),

  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    }),

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),

  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
}
