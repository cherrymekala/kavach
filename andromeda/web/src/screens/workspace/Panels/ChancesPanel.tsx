import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowRightIcon, CheckCircle2Icon, CircleIcon, ShieldCheckIcon } from 'lucide-react'
import { Argument, Button, type ArgumentSource } from '@/components'
import { SourceSheet } from '@/screens/chances/SourceSheet'
import { ExpertCard } from './ExpertCard'
import { usePack } from '@/api/hooks'
import type { Case } from '@/api/types'
import { cn } from '@/lib/cn'

const PILL: Record<string, string> = {
  strong: 'bg-accent text-accent-foreground',
  medium: 'bg-[#ffe3da] text-[#8f2207] dark:bg-[#3a1f19] dark:text-[#ffb49e]',
  weak: 'bg-muted text-muted-foreground',
}
// Without past cases to count, the ring shows the verdict level instead.
const LEVEL: Record<string, number> = { strong: 0.8, medium: 0.55, weak: 0.25 }
const RING = 2 * Math.PI * 44

/** The canvas's chances gauge: filled with the share of similar cases that patients won. */
function ChanceRing({ won, total, strength }: { won: number; total: number; strength: string }) {
  const id = useId().replace(/:/g, '')
  const value = total ? won / total : (LEVEL[strength] ?? 0.25)
  return (
    <svg viewBox="0 0 110 110" className="size-[110px] shrink-0" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FFC2AE" />
          <stop offset="1" stopColor="#FF5A36" />
        </linearGradient>
      </defs>
      <circle cx="55" cy="55" r="44" fill="none" className="stroke-accent" strokeWidth="12" />
      <circle
        className="kv-ring"
        cx="55"
        cy="55"
        r="44"
        fill="none"
        stroke={`url(#${id})`}
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={`${value * RING} ${RING}`}
        transform="rotate(-90 55 55)"
      />
      {total ? (
        <text x="55" y="62" textAnchor="middle" className="fill-foreground font-display text-[19px] font-bold">
          {won}/{total}
        </text>
      ) : null}
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
      <div className="animate-rise flex items-center gap-5 rounded-[28px] bg-card p-6 shadow-[0_18px_40px_rgb(46_31_184/0.08)]">
        <ChanceRing won={won} total={total} strength={strength} />
        <div className="flex min-w-0 flex-col gap-2">
          <span className={cn('w-fit rounded-full px-3 py-1 text-xs font-bold', PILL[strength] ?? PILL.weak)}>
            {t(`chances.strength.${strength}`)}
          </span>
          <h2 className="font-display text-xl leading-tight font-bold tracking-[-0.03em]">
            {total ? t('chances.won', { won, total }) : t(`chances.strength.${strength}`)}
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {total ? t('chances.fromRulings', { body }) : t(`chances.strengthHint.${strength}`)}
          </p>
        </div>
      </div>
      {total ? <p className="-mt-6 max-w-[56ch] text-[15px] leading-relaxed">{t(`chances.strengthHint.${strength}`)}</p> : null}

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

      <ExpertCard kase={kase} />

      <p className="max-w-[62ch] text-xs leading-relaxed text-muted-foreground">{assessment.disclaimer}</p>

      <SourceSheet source={source} onClose={() => setSource(null)} />
    </section>
  )
}
