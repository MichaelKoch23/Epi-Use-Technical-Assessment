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

/**
 * Renders whatever `avatarUrl` the API resolved (uploaded override, else a
 * Gravatar image - see `avatars.py`), falling back to initials on
 * `--brand-steel` if that URL 404s. Decorative (`alt=""`): the name always
 * sits next to the avatar, so a failed load never leaves a broken image.
 */
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
      {/* Keyed on the URL so a fresh image gets a fresh "has it failed?"
       * state instead of carrying over the previous row/avatar's result. */}
      <AvatarImage key={avatarUrl} avatarUrl={avatarUrl} fallback={initials(firstName, lastName)} />
    </span>
  )
}
