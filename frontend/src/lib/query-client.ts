import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,      // 2 minutes
      gcTime: 1000 * 60 * 10,         // 10 minutes
      retry: (failureCount, error) => {
        // Don't retry auth errors
        if (error instanceof Error && error.message === 'Unauthorized') return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
  },
})
