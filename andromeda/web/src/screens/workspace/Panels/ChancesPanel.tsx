import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2Icon, CircleIcon } from 'lucide-react'
import { Argument, type ArgumentSource } from '@/components'
import { SourceSheet } from '@/screens/chances/SourceSheet'
import { usePack } from '@/api/hooks'
import type { Case } from '@/api/types'
import { cn } from '@/lib/cn'

const LEVELS = ['weak', 'medium', 'strong'] as const
const LEVEL_TEXT: Record<string, string> = { strong: 'text-mint', medium: 'text-amber', weak: 'text-muted-foreground' }
const LEVEL_BAR: Record<string, string> = { strong: 'bg-mint', medium: 'bg-amber', weak: 'bg-muted-foreground' }

export function ChancesPanel({ kase }: { kase: Case }) {
  const { t } = useTranslation()
  const { data: pack } = usePack(kase?.country)
  const [source, setSource] = useState<ArgumentSource | null>(null)

  const assessment = kase.assessment
  if (!assessment) return null

  const level = Math.max(0, LEVELS.indexOf(assessment.strength as (typeof LEVELS)[number]))
  const args = assessment.arguments ?? []
  const missing = assessment.missing_documents ?? []
  const won = assessment.similar_cases_won ?? 0
  const total = assessment.similar_cases_total ?? 0
  const body = pack?.ladder.at(-1)?.step ?? t('chances.disputeBody')

  return (
    <section className="flex flex-col gap-5">
      <header>
        <h2 className="font-display text-xl font-bold">{t('chances.title')}</h2>
        <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <CheckCircle2Icon className="size-3.5 text-mint" aria-hidden />
          {t('chances.checked')}
        </p>
      </header>

      <div className="flex flex-col gap-3 border-y border-rule py-5">
        <p className={cn('font-display text-3xl font-extrabold leading-none', LEVEL_TEXT[assessment.strength])}>
          {t(`chances.strength.${assessment.strength}`)}
        </p>
        <div className="grid grid-cols-3 gap-1.5" aria-hidden>
          {LEVELS.map((l, i) => (
            <span key={l} className={cn('h-2 rounded-full', i <= level ? LEVEL_BAR[assessment.strength] : 'bg-muted')} />
          ))}
        </div>
        <p className="max-w-[60ch] text-sm text-muted-foreground">{t(`chances.strengthHint.${assessment.strength}`)}</p>

        {total ? (
          <p className="text-sm">
            <span className="font-display text-xl font-extrabold tabular-nums">
              {won}/{total}
            </span>{' '}
            <span className="text-muted-foreground">{t('chances.precedents', { body })}</span>
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-4">
        {args.length ? (
          args.map((a, i) => (
            <Argument
              key={`${i}-${a.claim}`}
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

      {missing.length ? (
        <div className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('chances.missing')}</h3>
          <ul className="flex flex-col gap-2">
            {missing.map((m) => (
              <li key={m} className="flex items-start gap-2 text-sm">
                <CircleIcon className="mt-0.5 size-4 shrink-0 text-amber" aria-hidden />
                {m}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="text-xs text-muted-foreground">{assessment.disclaimer}</p>

      <SourceSheet source={source} onClose={() => setSource(null)} />
    </section>
  )
}