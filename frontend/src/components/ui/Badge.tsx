import type { ReactNode } from 'react'

type Color = 'gray' | 'indigo' | 'green' | 'amber' | 'red'

interface BadgeProps {
  color?: Color
  children: ReactNode
  className?: string
}

const COLORS: Record<Color, string> = {
  gray:   'bg-gray-100 text-gray-700',
  indigo: 'bg-indigo-100 text-indigo-700',
  green:  'bg-green-100 text-green-700',
  amber:  'bg-amber-100 text-amber-800',
  red:    'bg-red-100 text-red-700',
}

export function Badge({ color = 'gray', children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${COLORS[color]} ${className}`}>
      {children}
    </span>
  )
}
