import { XIcon } from 'lucide-react'
import type { Chip } from './filterChips'

export function FilterChipRow({ chips }: { chips: Chip[] }) {
  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-foreground"
        >
          {chip.label}
          <button
            type="button"
            aria-label={`Remove ${chip.label} filter`}
            onClick={chip.onRemove}
            className="grid size-3.5 place-items-center rounded-full hover:bg-foreground/10"
          >
            <XIcon className="size-3" />
          </button>
        </span>
      ))}
    </div>
  )
}
