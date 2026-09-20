import { useState } from 'react'

export function AccountAvatar({ name, src, large = false }: { name: string; src?: string; large?: boolean }) {
  const [failed, setFailed] = useState(false)
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'W'
  const size = large ? 'size-16 text-lg' : 'size-8 text-xs'

  return (
    <span className={`relative grid shrink-0 place-items-center overflow-hidden rounded-full bg-surface font-mono text-muted ${size}`} aria-hidden="true">
      {src && !failed ? <img src={src} alt="" onError={() => setFailed(true)} className="absolute inset-0 size-full object-cover" /> : initials}
    </span>
  )
}
