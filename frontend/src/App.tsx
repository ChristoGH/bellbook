import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { getAccessToken, isTokenExpired } from './lib/auth'

// Auth routes (small — load eagerly)
import LoginPage from './routes/auth/login'
import RegisterPage from './routes/auth/register'

// App routes (lazy-loaded for faster initial paint)
const DashboardPage         = lazy(() => import('./routes/dashboard/index'))
const AnnouncementsPage     = lazy(() => import('./routes/announcements/index'))
const AnnouncementDetail    = lazy(() => import('./routes/announcements/detail'))
const CreateAnnouncement    = lazy(() => import('./routes/announcements/create'))
const MessagesPage          = lazy(() => import('./routes/messages/index'))
const ConversationPage      = lazy(() => import('./routes/messages/conversation'))
const CalendarPage          = lazy(() => import('./routes/calendar/index'))
const ProfilePage           = lazy(() => import('./routes/settings/profile'))

function PageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  )
}

/** Guards authenticated routes — redirects to /login if no valid token. */
function ProtectedRoute() {
  const token = getAccessToken()
  if (!token || isTokenExpired(token)) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

export default function App() {
  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        {/* Public routes */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/"                          element={<DashboardPage />} />
            <Route path="/announcements"             element={<AnnouncementsPage />} />
            <Route path="/announcements/create"      element={<CreateAnnouncement />} />
            <Route path="/announcements/:id"         element={<AnnouncementDetail />} />
            <Route path="/messages"                  element={<MessagesPage />} />
            <Route path="/messages/:id"              element={<ConversationPage />} />
            <Route path="/calendar"                  element={<CalendarPage />} />
            <Route path="/settings"                  element={<ProfilePage />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
