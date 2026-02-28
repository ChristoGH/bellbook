import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
}

export function Card({ children, className = '', onClick }: CardProps) {
  const base = 'rounded-2xl bg-white shadow-sm border border-gray-100'
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${base} w-full text-left transition-shadow hover:shadow-md active:scale-[0.99] ${className}`}
      >
        {children}
      </button>
    )
  }
  return <div className={`${base} ${className}`}>{children}</div>
}
