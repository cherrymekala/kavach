import { ArrowLeftIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'

export interface AppHeaderProps {
  title: string
  onBack?: () => void
  right?: ReactNode
  /** Country pack label, e.g. "IN" or "SG". */
  pack?: string
}

export function AppHeader({ title, onBack, right, pack }: AppHeaderProps) {
  return (
    <div className="flex items-center gap-3">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="grid size-9 shrink-0 place-items-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <ArrowLeftIcon className="size-5" />
        </button>
      ) : null}
      <h1 className="min-w-0 flex-1 truncate font-display text-2xl font-extrabold tracking-tight">{title}</h1>
      {pack ? <Badge variant="secondary">{pack}</Badge> : null}
      {right}
    </div>
  )
}