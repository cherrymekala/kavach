import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { KavachMark } from './kavach-plates'

export type ShieldTone = 'brand' | 'good' | 'mixed' | 'low'

// The tone shows in the eyebrow pill; the card itself stays white (no dark surfaces).
const PILL: Record<ShieldTone, string> = {
  brand: 'bg-accent text-accent-foreground',
  good: 'bg-accent text-accent-foreground',
  mixed: 'bg-[#ffe3da] text-[#8f2207] dark:bg-[#3a1f19] dark:text-[#ffb49e]',
  low: 'bg-muted text-muted-foreground',
}

/**
 * The key message of a panel: a white card with the title in the display face, a tone
 * pill, and the Kavach mark faint in the corner.
 */
export function ShieldHero({ tone = 'brand', eyebrow, children, footer, actions }: {
  tone?: ShieldTone
  eyebrow?: ReactNode
  children: ReactNode
  footer?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="animate-rise relative overflow-hidden rounded-[28px] bg-card px-6 pt-6 pb-7 text-card-foreground shadow-[0_18px_40px_rgb(46_31_184/0.08)]">
      <KavachMark animate={false} className="pointer-events-none absolute -right-6 -bottom-8 h-44 text-brand opacity-[0.07]" />
      <div className="relative flex flex-col gap-3">
        {eyebrow ? (
          <span className={cn('w-fit rounded-full px-3 py-1 text-xs font-bold', PILL[tone])}>{eyebrow}</span>
        ) : null}
        <div className="max-w-[24ch] font-display text-[1.6rem] leading-[1.15] font-bold tracking-[-0.03em]">{children}</div>
        {footer ? <div className="max-w-[44ch] text-[15px] leading-relaxed text-muted-foreground">{footer}</div> : null}
        {actions ? <div className="mt-2 flex flex-col gap-2 sm:flex-row [&_[data-slot=button]]:h-12 [&_[data-slot=button]]:px-6">{actions}</div> : null}
      </div>
    </div>
  )
}
