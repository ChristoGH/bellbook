import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

interface TopBarProps {
  title: string
  back?: boolean
  action?: ReactNode
}

export function TopBar({ title, back, action }: TopBarProps) {
  const navigate = useNavigate()

  return (
    <header className="fixed top-0 left-0 right-0 z-40 border-b border-gray-200 bg-white"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}>
      <div className="mx-auto flex h-14 max-w-lg items-center gap-3 px-4">
        {back && (
          <button
            onClick={() => navigate(-1)}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
            aria-label="Go back"
          >
            <ArrowLeft size={20} />
          </button>
        )}
        <h1 className="flex-1 text-lg font-semibold text-gray-900 truncate">{title}</h1>
        {action && <div className="flex items-center">{action}</div>}
      </div>
    </header>
  )
}
