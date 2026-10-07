import { ArrowLeftIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export interface AppHeaderProps {
  title: string
  onBack?: () => void
  right?: ReactNode
  /** Country pack label, e.g. "IN" or "SG". */
  pack?: string
}

export function AppHeader({ title, onBack, right, pack }: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-border bg-background/90 px-4 py-3 backdrop-blur">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="grid size-9 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <ArrowLeftIcon className="size-5" />
        </button>
      ) : null}
      <h1 className="min-w-0 flex-1 truncate font-display text-lg font-bold">{title}</h1>
      {pack ? (
        <span className="shrink-0 rounded-full bg-accent px-2.5 py-0.5 font-mono text-[11px] font-semibold text-accent-foreground">
          {pack} pack
        </span>
      ) : null}
      {right}
    </header>
  )
}