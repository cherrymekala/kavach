import { CheckIcon } from 'lucide-react'
import { cn } from '@/lib/cn'

export interface StepperProps {
  steps: { label: string; detail?: string }[]
  current: number
}

/** Dispute ladder — done (mint), now (amber), pending. */
export function Stepper({ steps, current }: StepperProps) {
  return (
    <ol className="flex flex-col gap-3">
      {steps.map((s, i) => {
        const done = i < current
        const now = i === current
        return (
          <li key={s.label} className="flex items-start gap-3">
            <span
              className={cn(
                'grid size-7 shrink-0 place-items-center rounded-full text-sm font-bold',
                done ? 'bg-mint text-surface' : now ? 'bg-amber text-surface' : 'bg-muted text-muted-foreground',
              )}
            >
              {done ? <CheckIcon className="size-4" aria-hidden /> : i + 1}
            </span>
            <div className="min-w-0">
              <p className={cn('font-semibold', done && 'text-muted-foreground')}>{s.label}</p>
              {s.detail ? <p className="text-sm text-muted-foreground">{s.detail}</p> : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}