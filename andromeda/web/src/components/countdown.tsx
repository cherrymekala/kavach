import { daysUntil } from '@/lib/dates'
import { cn } from '@/lib/cn'

export function Countdown({ deadline, className }: { deadline: string | null | undefined; className?: string }) {
  const days = daysUntil(deadline)
  if (days === null) return null
  const urgent = days <= 5
  return (
    <span
      className={cn(
        'font-mono text-sm font-semibold tabular-nums',
        urgent ? 'text-amber' : 'text-muted-foreground',
        className,
      )}
    >
      {days <= 0 ? 'Overdue' : `${days} day${days === 1 ? '' : 's'} left`}
    </span>
  )
}