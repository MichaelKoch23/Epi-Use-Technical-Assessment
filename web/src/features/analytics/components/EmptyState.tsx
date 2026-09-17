import type { ComponentType } from 'react'
import { InboxIcon } from 'lucide-react'

export function EmptyState({
  icon: Icon = InboxIcon,
  title,
  children,
  action,
}: {
  icon?: ComponentType<{ className?: string }>
  title: string
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="rounded-md border border-dashed border-border bg-card px-6 py-12 text-center">
      <div className="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-muted text-muted-foreground">
        <Icon className="size-6" />
      </div>
      <p className="font-display mb-2 text-lg font-bold text-foreground">{title}</p>
      <p className="mx-auto mb-4 max-w-prose text-sm text-muted-foreground">{children}</p>
      {action}
    </div>
  )
}
