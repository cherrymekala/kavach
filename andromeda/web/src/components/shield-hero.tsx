import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export type ShieldTone = 'brand' | 'good' | 'mixed' | 'low'

// Fixed deep shades (not theme tokens): white text must pass contrast in light and dark.
const TONE: Record<ShieldTone, string> = {
  brand: 'bg-[#1d5c4d] text-white',
  good: 'bg-[#1d5c4d] text-white',
  mixed: 'bg-[#8a5514] text-white',
  low: 'bg-[#45443e] text-white',
}

/**
 * The one coloured moment on a panel: the thing the patient needs to know, on Kavach's
 * evergreen, with the shield (kavach) drawn large behind it.
 */
export function ShieldHero({ tone = 'brand', eyebrow, children, footer, actions }: {
  tone?: ShieldTone
  eyebrow?: ReactNode
  children: ReactNode
  footer?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className={cn('animate-rise relative overflow-hidden rounded-3xl px-6 pt-6 pb-7', TONE[tone])}>
      <svg
        viewBox="0 0 120 140"
        className="pointer-events-none absolute -right-6 -bottom-8 h-44 w-auto opacity-[0.13]"
        aria-hidden
      >
        <path
          d="M60 4 L112 22 V66 C112 100 90 124 60 136 C30 124 8 100 8 66 V22 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinejoin="round"
        />
        <path d="M38 70 L54 86 L84 54" fill="none" stroke="currentColor" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="relative flex flex-col gap-3">
        {eyebrow ? <div className="text-sm font-semibold opacity-85">{eyebrow}</div> : null}
        <div className="max-w-[22ch] text-[1.75rem] leading-[1.15] font-extrabold tracking-tight">{children}</div>
        {footer ? <div className="max-w-[40ch] text-[15px] leading-relaxed opacity-90">{footer}</div> : null}
        {actions ? (
          // Buttons on the coloured panel turn white so they stay the obvious next step.
          <div className="mt-2 flex flex-col gap-2 sm:flex-row [&_[data-slot=button]]:h-11 [&_[data-slot=button]]:rounded-full [&_[data-slot=button]]:bg-white [&_[data-slot=button]]:px-6 [&_[data-slot=button]]:text-[#1d5c4d] [&_[data-slot=button]]:hover:bg-white/90">
            {actions}
          </div>
        ) : null}
      </div>
    </div>
  )
}
