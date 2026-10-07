import { cn } from '@/lib/cn'

export type MeterTone = 'mint' | 'brand' | 'amber'

export interface MeterProps {
  /** 0..1 */
  value: number
  tone?: MeterTone
  className?: string
}

/** Deterministic progress/strength bar (0..1). For indeterminate loading use Progress. */
export function Meter({ value, tone = 'mint', className }: MeterProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn('h-2.5 w-full overflow-hidden rounded-full bg-muted', className)}
    >
      <div
        className={cn(
          'h-full rounded-full',
          tone === 'mint' && 'bg-mint',
          tone === 'brand' && 'bg-brand',
          tone === 'amber' && 'bg-amber',
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}