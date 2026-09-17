import { useState } from 'react'
import { cn } from '@/lib/utils'

function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
}

function AvatarImage({ avatarUrl, fallback }: { avatarUrl: string; fallback: string }) {
  const [failed, setFailed] = useState(false)
  if (failed) return <>{fallback}</>
  return (
    <img
      src={avatarUrl}
      alt=""
      className="size-full object-cover"
      onError={() => setFailed(true)}
    />
  )
}

export function EmployeeAvatar({
  avatarUrl,
  firstName,
  lastName,
  size = 32,
  className,
}: {
  avatarUrl: string
  firstName: string
  lastName: string
  size?: number
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-steel text-xs font-semibold text-brand-primary',
        className
      )}
      style={{ width: size, height: size }}
    >
      <AvatarImage key={avatarUrl} avatarUrl={avatarUrl} fallback={initials(firstName, lastName)} />
    </span>
  )
}
