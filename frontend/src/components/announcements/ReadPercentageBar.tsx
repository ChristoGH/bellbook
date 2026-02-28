interface ReadPercentageBarProps {
  percentage: number
  showLabel?: boolean
}

function colorClass(pct: number) {
  if (pct >= 80) return 'bg-green-500'
  if (pct >= 50) return 'bg-amber-400'
  return 'bg-red-500'
}

export function ReadPercentageBar({ percentage, showLabel = true }: ReadPercentageBarProps) {
  const pct = Math.min(100, Math.max(0, percentage))
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all ${colorClass(pct)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className="w-10 text-right text-xs font-medium text-gray-600">
          {pct.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
