import { Outlet } from 'react-router-dom'
import { BottomNav } from './BottomNav'
import { useSSE } from '../../hooks/useSSE'

/** Root layout for all authenticated screens. */
export function AppShell() {
  // Connect SSE once at the shell level — persists across route changes
  useSSE()

  return (
    <div className="flex min-h-screen flex-col">
      {/* Route-specific top bars are rendered inside each route */}
      <main className="flex-1 mx-auto w-full max-w-lg pb-nav">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
