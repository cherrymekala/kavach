import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react'
import { cn } from '@/lib/cn'
import { SourceKindIcon } from './source-kind-icon'

export interface ArgumentSource {
  ref: string
  quote?: string
  kind?: string
}

export interface ArgumentProps {
  index: number
  claim: string
  explanation: string
  sources: ArgumentSource[]
  onSource?: (source: ArgumentSource) => void
}

/** Our citations carry file names for uploaded documents; show the kind of document instead. */
function isFileName(ref: string): boolean {
  return /\.(txt|pdf|jpe?g|png|webp)$/i.test(ref)
}

/** One sourced argument: a numbered reason, the proof behind it, and the long version folded away. */
export function Argument({ index, claim, explanation, sources, onSource }: ArgumentProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  return (
    <article className="flex gap-4">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent text-sm font-extrabold text-accent-foreground">
        {index + 1}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <h3 className="pt-0.5 text-[17px] leading-snug font-bold">{claim}</h3>

        {sources.length ? (
          <ul className="flex flex-col gap-2">
            {sources.map((s, i) => {
              const kind = s.kind ?? 'other'
              return (
                <li key={`${s.ref}-${i}`}>
                  <button
                    type="button"
                    onClick={() => onSource?.(s)}
                    className="flex w-full items-start gap-3 rounded-2xl bg-muted/70 p-3.5 text-left transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <SourceKindIcon kind={kind} className="mt-0.5 size-4 shrink-0 text-brand" />
                    <span className="flex min-w-0 flex-1 flex-col gap-1">
                      {s.quote ? <span className="line-clamp-3 text-sm leading-relaxed">“{s.quote}”</span> : null}
                      <span className="truncate text-xs text-muted-foreground">
                        <span className="font-semibold text-foreground">{t(`chances.kind.${kind}`, { defaultValue: kind })}</span>
                        {!isFileName(s.ref) ? ` · ${s.ref}` : null}
                      </span>
                    </span>
                    <ChevronRightIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}

        {explanation ? (
          <div>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="flex items-center gap-1 text-sm font-semibold text-brand"
            >
              {t('chances.why')}
              <ChevronDownIcon className={cn('size-4 transition-transform', open && 'rotate-180')} aria-hidden />
            </button>
            {open ? <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-muted-foreground">{explanation}</p> : null}
          </div>
        ) : null}
      </div>
    </article>
  )
}
