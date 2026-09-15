import { useEffect, useState } from 'react'
import { gravatarUrl } from '@/lib/gravatar'
import { cn } from '@/lib/utils'

function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
}

export function EmployeeAvatar({
  email,
  firstName,
  lastName,
  overrideUrl,
  size = 32,
  className,
}: {
  email: string
  firstName: string
  lastName: string
  overrideUrl?: string | null
  size?: number
  className?: string
}) {
  const [gravatar, setGravatar] = useState<string | null>(null)
  const [imgFailed, setImgFailed] = useState(false)

  useEffect(() => {
    setImgFailed(false)
    if (overrideUrl) return
    let cancelled = false
    gravatarUrl(email, size * 2).then((url) => {
      if (!cancelled) setGravatar(url)
    })
    return () => {
      cancelled = true
    }
  }, [email, overrideUrl, size])

  const src = overrideUrl ?? gravatar
  const showImage = Boolean(src) && !imgFailed

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-steel text-xs font-semibold text-brand-primary',
        className
      )}
      style={{ width: size, height: size }}
    >
      {showImage ? (
        // Decorative: the name always sits next to the avatar, so a failed
        // load falls back to initials rather than a broken-image icon.
        <img
          src={src ?? undefined}
          alt=""
          className="size-full object-cover"
          onError={() => setImgFailed(true)}
        />
      ) : (
        initials(firstName, lastName)
      )}
    </span>
  )
}
