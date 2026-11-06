import { useId, useRef, useState, type PointerEvent } from 'react'
import { cn } from '@/lib/cn'

/** The three plates of the shield, top to bottom (viewBox units, from the Kavach Mobile canvas). */
const PLATES = [
  'M80 110 195 150 310 110 310 170 195 214 80 170Z',
  'M88 196 195 236 302 196 302 252 195 296 88 252Z',
  'M104 282 195 318 286 282 280 322 195 390 110 322Z',
] as const

const DELAY = ['0.05s', '0.3s', '0.55s'] as const

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export interface KavachPlatesProps {
  /** Rendered width in px; height follows the shield's proportions. */
  size?: number
  /**
   * How many plates are forged (0–3). Leave unset for the brand moment: all three drop in
   * and the bottom plate ignites. With a number, the next plate is drawn as a dashed
   * outline being forged, so the shield is the progress bar.
   */
  formed?: number
  /** Floating dots around the shield (the outcome's celebration). */
  celebrate?: boolean
  /** Tilt toward the pointer on devices that have one. */
  interactive?: boolean
  className?: string
}

/**
 * Kavach's 3D mark: three glass plates of lamellar armour. Each plate is an agent; the
 * bottom one turns vermilion, the plate that holds. Decorative: callers carry the meaning
 * in text.
 */
export function KavachPlates({ size = 220, formed, celebrate = false, interactive = true, className }: KavachPlatesProps) {
  const id = useId().replace(/:/g, '')
  const ref = useRef<HTMLDivElement>(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0 })
  const assemble = formed === undefined
  const count = assemble ? 3 : Math.max(0, Math.min(3, formed))

  function onMove(e: PointerEvent<HTMLDivElement>) {
    if (!interactive || e.pointerType !== 'mouse' || prefersReducedMotion() || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    setTilt({ x: ((e.clientY - r.top) / r.height - 0.5) * -14, y: ((e.clientX - r.left) / r.width - 0.5) * 18 })
  }

  return (
    <div
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
      className={cn('shrink-0', className)}
      style={{ width: size, perspective: 900 }}
      aria-hidden
    >
      <svg
        viewBox="40 50 310 420"
        className="block h-auto w-full overflow-visible transition-transform duration-300 ease-out"
        style={{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
      >
        <defs>
          <linearGradient id={`${id}p1`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#FFFFFF" />
            <stop offset="0.45" stopColor="#D9D5FF" />
            <stop offset="1" stopColor="#8E84F5" />
          </linearGradient>
          <linearGradient id={`${id}p2`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#C9C3FF" />
            <stop offset="0.5" stopColor="#6A5BF0" />
            <stop offset="1" stopColor="#2E1FB8" />
          </linearGradient>
          <linearGradient id={`${id}p3`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#FFC2AE" />
            <stop offset="0.5" stopColor="#FF5A36" />
            <stop offset="1" stopColor="#B32708" />
          </linearGradient>
          <linearGradient id={`${id}edge`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
          </linearGradient>
          <radialGradient id={`${id}floor`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#3B2BD9" stopOpacity="0.28" />
            <stop offset="1" stopColor="#3B2BD9" stopOpacity="0" />
          </radialGradient>
          <filter id={`${id}sh`} x="-30%" y="-30%" width="160%" height="180%">
            <feDropShadow dx="0" dy="16" stdDeviation="14" floodColor="#2E1FB8" floodOpacity="0.3" />
          </filter>
        </defs>

        <ellipse className="kv-floor" cx="195" cy="440" rx="130" ry="20" fill={`url(#${id}floor)`} />

        <g className="kv-bob">
          {PLATES.map((d, i) => {
            if (i < count) {
              return (
                // Keyed by index so a newly forged plate drops in when progress reaches it.
                <g key={`on-${i}`} className="kv-plate" style={{ animationDelay: assemble ? DELAY[i] : '0s' }} filter={`url(#${id}sh)`}>
                  <path d={d} fill={`url(#${id}p${i + 1})`} />
                  <path d={d.split(' ').slice(0, 6).join(' ')} fill="none" stroke={`url(#${id}edge)`} strokeWidth="3" />
                </g>
              )
            }
            if (i === count) {
              return <path key={`forge-${i}`} className="kv-dash" d={d} fill="none" stroke="#FF5A36" strokeWidth="3" strokeDasharray="8 8" />
            }
            return <path key={`off-${i}`} d={d} fill="none" stroke="currentColor" strokeOpacity="0.15" strokeWidth="2" />
          })}
          {/* The bottom plate arrives lavender and ignites to vermilion: the plate that holds. */}
          {assemble ? <path className="kv-ignite" d={PLATES[2]} fill={`url(#${id}p1)`} /> : null}
        </g>

        {celebrate ? (
          <>
            <circle className="kv-dot" cx="90" cy="100" r="8" fill={`url(#${id}p3)`} />
            <circle className="kv-dot" style={{ animationDelay: '-2s' }} cx="300" cy="80" r="12" fill={`url(#${id}p2)`} />
            <circle className="kv-dot" style={{ animationDelay: '-4s' }} cx="250" cy="60" r="5" fill={`url(#${id}p1)`} />
          </>
        ) : null}
      </svg>
    </div>
  )
}

/** The flat logo mark (shield outline, two ink chevrons, one vermilion), drawn in on mount. */
export function KavachMark({ className, animate = true }: { className?: string; animate?: boolean }) {
  return (
    <svg viewBox="0 0 60 68" className={cn('h-8 w-auto', className)} role="img" aria-label="Kavach">
      <path className={animate ? 'kv-draw' : undefined} d="M30 2 56 11v22c0 17-11 29-26 33C15 62 4 50 4 33V11z" fill="none" stroke="currentColor" strokeWidth="4" />
      <path className={animate ? 'kv-draw' : undefined} d="M14 22 30 29 46 22" fill="none" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" strokeLinecap="round" />
      <path className={animate ? 'kv-pop' : undefined} d="M14 38 30 45 46 38" fill="none" stroke="#FF5A36" strokeWidth="6" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
