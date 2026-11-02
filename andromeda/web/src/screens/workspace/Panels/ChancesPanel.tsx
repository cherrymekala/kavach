import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowRightIcon, CheckCircle2Icon, CircleIcon, ShieldCheckIcon } from 'lucide-react'
import { Argument, Button, ShieldHero, type ArgumentSource, type ShieldTone } from '@/components'
import { SourceSheet } from '@/screens/chances/SourceSheet'
import { usePack } from '@/api/hooks'
import type { Case } from '@/api/types'
import { cn } from '@/lib/cn'

const TONE: Record<string, ShieldTone> = { strong: 'good', medium: 'mixed', weak: 'low' }

/** A small figure for one past case; filled when the patient was paid. */
function Person({ won }: { won: boolean }) {
  return (
    <svg viewBox="0 0 16 24" className={cn('h-7 w-auto', won ? 'text-brand' : 'text-muted-foreground/30')} aria-hidden>
      <circle cx="8" cy="5" r="4" fill="currentColor" />
      <path d="M1 23 V16 C1 12 4 10 8 10 C12 10 15 12 15 16 V23 Z" fill="currentColor" />
    </svg>
  )
}

export function ChancesPanel({ kase, onNext }: { kase: Case; onNext?: () => void }) {
  const { t } = useTranslation()
  const { data: pack } = usePack(kase?.country)
  const [source, setSource] = useState<ArgumentSource | null>(null)

  const assessment = kase.assessment
  if (!assessment) return null

  const strength = assessment.strength
  const args = assessment.arguments ?? []
  const missing = assessment.missing_documents ?? []
  const won = assessment.similar_cases_won ?? 0
  const total = assessment.similar_cases_total ?? 0
  const body = pack?.ladder.at(-1)?.step ?? t('chances.disputeBody')

  return (
    <section className="flex flex-col gap-10">
      <ShieldHero
        tone={TONE[strength] ?? 'low'}
        eyebrow={t('chances.title')}
        footer={t(`chances.strengthHint.${strength}`)}
      >
        {t(`chances.strength.${strength}`)}
      </ShieldHero>

      {total ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-1.5" role="img" aria-label={t('chances.won', { won, total })}>
            {Array.from({ length: total }, (_, i) => (
              <Person key={i} won={i < won} />
            ))}
          </div>
          <p className="max-w-[44ch] text-[15px] leading-relaxed">
            {t('chances.peopleWon', { won, total, body })}
          </p>
        </div>
      ) : null}

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-extrabold tracking-tight">{t('chances.arguments', { count: args.length })}</h2>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <ShieldCheckIcon className="size-4 text-brand" aria-hidden />
            {t('chances.checked')}
          </p>
        </div>
        {args.length ? (
          args.map((a, i) => (
            <Argument
              key={`${i}-${a.claim}`}
              index={i}
              claim={a.claim}
              explanation={a.explanation}
              sources={a.sources.map((s) => ({ ref: s.ref, quote: s.quote, kind: s.kind }))}
              onSource={setSource}
            />
          ))
        ) : (
          <p className="text-sm text-muted-foreground">{t('chances.noArguments')}</p>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-xl font-extrabold tracking-tight">{t('chances.missing')}</h2>
        {missing.length ? (
          <ul className="flex flex-col gap-2">
            {missing.map((m) => (
              <li key={m} className="flex items-start gap-3 rounded-2xl border border-border p-3.5 text-sm leading-relaxed">
                <CircleIcon className="mt-0.5 size-4 shrink-0 text-amber" aria-hidden />
                {m}
              </li>
            ))}
          </ul>
        ) : (
          <p className="flex items-center gap-2 text-sm text-mint">
            <CheckCircle2Icon className="size-4" aria-hidden />
            {t('chances.noMissing')}
          </p>
        )}
      </div>

      {onNext ? (
        <Button size="lg" onClick={onNext} className="h-12 w-full rounded-full text-base sm:w-auto sm:self-start sm:px-8">
          {t('chances.cta')}
          <ArrowRightIcon aria-hidden />
        </Button>
      ) : null}

      <p className="max-w-[62ch] text-xs leading-relaxed text-muted-foreground">{assessment.disclaimer}</p>

      <SourceSheet source={source} onClose={() => setSource(null)} />
    </section>
  )
}
