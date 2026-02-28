import { NavLink } from 'react-router-dom'
import { Home, MessageSquare, Calendar, User } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/',            label: 'Home',     Icon: Home },
  { to: '/messages',   label: 'Messages', Icon: MessageSquare },
  { to: '/calendar',   label: 'Calendar', Icon: Calendar },
  { to: '/settings',   label: 'Profile',  Icon: User },
] as const

export function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white"
         style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <div className="mx-auto flex max-w-lg">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs font-medium transition-colors ${
                isActive ? 'text-indigo-600' : 'text-gray-500 hover:text-gray-700'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 1.75} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
