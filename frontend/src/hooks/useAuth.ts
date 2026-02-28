import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { clearTokens, getRefreshToken } from '../lib/auth'
import type { User } from '../types'

export function useAuth() {
  const queryClient = useQueryClient()

  const { data: user, isLoading, isError } = useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<User>('/auth/me'),
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const logout = async () => {
    const refresh = getRefreshToken()
    if (refresh) {
      await api.post('/auth/logout', { refresh_token: refresh }).catch(() => {})
    }
    clearTokens()
    queryClient.clear()
    window.location.href = '/login'
  }

  return {
    user: isError ? null : user ?? null,
    isLoading,
    isAuthenticated: !!user && !isError,
    logout,
  }
}
