interface AvatarProps {
  name: string
  src?: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-14 w-14 text-lg',
}

function initials(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
}

// Stable colour from name string (10 indigo/teal shades)
function avatarColor(name: string) {
  const colors = [
    'bg-indigo-500', 'bg-violet-500', 'bg-teal-500', 'bg-sky-500',
    'bg-emerald-500', 'bg-pink-500', 'bg-orange-500', 'bg-amber-500',
    'bg-cyan-500', 'bg-rose-500',
  ]
  const code = [...name].reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return colors[code % colors.length]
}

export function Avatar({ name, src, size = 'md', className = '' }: AvatarProps) {
  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={`${SIZE[size]} rounded-full object-cover ${className}`}
      />
    )
  }
  return (
    <div
      className={`${SIZE[size]} ${avatarColor(name)} flex items-center justify-center
        rounded-full font-semibold text-white ${className}`}
      aria-label={name}
    >
      {initials(name)}
    </div>
  )
}
