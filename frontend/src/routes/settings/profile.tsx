import { useAuth } from '../../hooks/useAuth'
import { TopBar } from '../../components/layout/TopBar'
import { Avatar } from '../../components/ui/Avatar'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'

const ROLE_LABEL: Record<string, string> = {
  parent: 'Parent',
  teacher: 'Teacher',
  school_admin: 'School Admin',
  super_admin: 'Super Admin',
}

export default function ProfilePage() {
  const { user, logout } = useAuth()

  if (!user) return null

  return (
    <>
      <TopBar title="Profile" />
      <div className="pt-14 px-4 py-6 flex flex-col gap-4">
        {/* User card */}
        <Card className="p-5 flex items-center gap-4">
          <Avatar name={`${user.first_name} ${user.last_name}`} src={user.avatar_url} size="lg" />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-gray-900 truncate">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-sm text-gray-500 truncate">{user.email ?? user.phone}</p>
            <Badge color="indigo" className="mt-1">{ROLE_LABEL[user.role] ?? user.role}</Badge>
          </div>
        </Card>

        {/* Actions */}
        <Card className="overflow-hidden divide-y divide-gray-100">
          {[
            { label: 'Notification settings', href: '#' },
            { label: 'Language / Taal',        href: '#' },
            { label: 'Privacy policy',         href: '#' },
          ].map(({ label }) => (
            <button
              key={label}
              className="flex w-full items-center justify-between px-4 py-3.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {label}
              <span className="text-gray-400">›</span>
            </button>
          ))}
        </Card>

        <Button variant="danger" className="w-full" onClick={logout}>
          Sign out
        </Button>
      </div>
    </>
  )
}
