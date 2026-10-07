import { cn } from '@/lib/cn'

export interface TimelineProps {
  items: { label: string; detail?: string; hot?: boolean }[]
}

/** Vertical timeline; `hot` highlights the current moment in mint. */
export function Timeline({ items }: TimelineProps) {
  return (
    <ol className="flex flex-col gap-3 border-l-2 border-line pl-4">
      {items.map((it) => (
        <li key={it.label} className="relative">
          <span
            className={cn(
              'absolute -left-[22px] top-1 size-3 rounded-full border-2',
              it.hot ? 'border-mint bg-mint' : 'border-brand bg-background',
            )}
          />
          <p className="font-semibold leading-tight">{it.label}</p>
          {it.detail ? <p className="text-sm text-muted-foreground">{it.detail}</p> : null}
        </li>
      ))}
    </ol>
  )
}