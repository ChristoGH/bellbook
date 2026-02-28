import { Badge } from '../ui/Badge'
import type { Priority } from '../../types'

interface PriorityBadgeProps {
  priority: Priority
}

const CONFIG = {
  urgent: { color: 'red'   as const, label: 'Urgent' },
  normal: { color: 'indigo' as const, label: 'Notice' },
  info:   { color: 'gray'  as const, label: 'Info' },
}

export function PriorityBadge({ priority }: PriorityBadgeProps) {
  const { color, label } = CONFIG[priority]
  return <Badge color={color}>{label}</Badge>
}
