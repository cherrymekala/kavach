import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertOctagonIcon, AlertTriangleIcon, BadgeCheckIcon, CheckCircle2Icon, InfoIcon } from 'lucide-react'
import { SourceKindIcon, type ArgumentSource, ShieldHero } from '@/components'
import { SourceSheet } from '@/screens/chances/SourceSheet'
import type { DischargeCheck, Risk } from '@/api/types'
import { cn } from '@/lib/cn'

// Severity is a status: always icon + label, never colour alone.
const SEVERITY = {
  high: { icon: AlertOctagonIcon, tone: 'text-destructive', ring: 'border-destructive/40' },
  medium: { icon: AlertTriangleIcon, tone: 'text-amber', ring: 'border-amber/50' },
  low: { icon: InfoIcon, tone: 'text-muted-foreground', ring: 'border-border' },
} as const

function RiskCard({ risk, onSource }: { risk: Risk; onSource: (s: ArgumentSource) => void }) {
  const { t } = useTranslation()
  const s = SEVERITY[risk.severity as keyof typeof SEVERITY] ?? SEVERITY.medium
  const Icon = s.icon
  return (
    <article className={cn('flex flex-col gap-3 rounded-2xl border bg-card p-5', s.ring)}>
      <p className={cn('flex items-center gap-1.5 text-xs font-semibold', s.tone)}>
        <Icon className="size-4" aria-hidden />
        {t(`discharge.severity.${risk.severity}`, { defaultValue: risk.severity })}
      </p>
      <h3 className="font-semibold leading-snug">{risk.title}</h3>
      <p className="text-sm text-muted-foreground">{risk.why}</p>
      <div className="rounded-lg bg-accent/60 p-3 text-sm">
        <p className="font-semibold">{t('discharge.fix')}</p>
        <p>{risk.fix}</p>
      </div>
      <div className="flex flex-col gap-2">
        {risk.sources.map((src, i) => (
          <button
            key={`${src.ref}-${i}`}
            type="button"
            onClick={() => onSource({ kind: src.kind, ref: src.ref, quote: src.quote })}
            className="flex w-full flex-col gap-1 rounded-2xl bg-muted/70 p-3.5 text-left hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            <span className="flex items-center gap-1.5 text-xs font-semibold text-brand">
              <SourceKindIcon kind={src.kind} className="size-3.5" />
              <span className="shrink-0">{t(`chances.kind.${src.kind}`, { defaultValue: src.kind })}</span>
              <span className="min-w-0 truncate font-normal text-muted-foreground">· {src.ref}</span>
              <BadgeCheckIcon className="ml-auto size-3.5 shrink-0 text-mint" aria-label={t('chances.verified')} />
            </span>
            <span className="line-clamp-3 text-sm leading-relaxed">“{src.quote}”</span>
          </button>
        ))}
      </div>
    </article>
  )
}

// A sentence ends at . ! ? before a capital letter, but not after "Rs.", "Dr.", initials like "S." and similar.
const SENTENCE_END = /(?<!\b(?:[A-Z]|Rs|Dr|Mr|Mrs|Ms|No|Sr|St|Sec|cl|Cl|vs|etc)\.)(?<=[.!?])\s+(?=[A-Z])/

export function DischargePanel({ check }: { check: DischargeCheck }) {
  const { t } = useTranslation()
  const [source, setSource] = useState<ArgumentSource | null>(null)
  const clear = check.verdict === 'clear'
  // The panel carries the headline sentence only; the rest of the summary reads as body text below.
  const [lead, ...rest] = check.summary.split(SENTENCE_END)

  return (
    <section className="flex flex-col gap-5">
      <ShieldHero
        tone={clear ? 'good' : check.verdict === 'high_risk' ? 'low' : 'mixed'}
        eyebrow={t('discharge.title')}
        footer={lead}
      >
        {t(`discharge.verdict.${check.verdict}`, { defaultValue: check.verdict })}
      </ShieldHero>
      {rest.length ? <p className="max-w-[62ch] text-[15px] leading-relaxed">{rest.join(' ')}</p> : null}
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <CheckCircle2Icon className="size-4 text-brand" aria-hidden />
        {t('chances.checked')}
      </p>

      {check.risks.length ? (
        <div className="flex flex-col gap-3">
          <h3 className="text-xl font-extrabold tracking-tight">{t('discharge.risks', { count: check.risks.length })}</h3>
          {check.risks.map((r, i) => (
            <RiskCard key={`${i}-${r.title}`} risk={r} onSource={setSource} />
          ))}
        </div>
      ) : (
        <p className="flex items-center gap-2 text-sm text-mint">
          <CheckCircle2Icon className="size-4" aria-hidden />
          {t('discharge.noRisks')}
        </p>
      )}

      <p className="text-xs text-muted-foreground">{check.disclaimer}</p>
      <SourceSheet source={source} onClose={() => setSource(null)} />
    </section>
  )
}
