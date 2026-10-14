import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertOctagonIcon, AlertTriangleIcon, BadgeCheckIcon, CheckCircle2Icon, InfoIcon } from 'lucide-react'
import { SourceKindIcon, type ArgumentSource } from '@/components'
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
    <article className={cn('flex flex-col gap-3 rounded-2xl border bg-card p-4', s.ring)}>
      <p className={cn('flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide', s.tone)}>
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
            className="flex w-full flex-col gap-1 rounded-lg bg-muted/60 p-3 text-left hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            <span className="flex items-center gap-1.5 text-xs font-semibold text-brand">
              <SourceKindIcon kind={src.kind} className="size-3.5" />
              <span className="shrink-0">{t(`chances.kind.${src.kind}`, { defaultValue: src.kind })}</span>
              <span className="min-w-0 truncate font-normal text-muted-foreground">· {src.ref}</span>
              <BadgeCheckIcon className="ml-auto size-3.5 shrink-0 text-mint" aria-label={t('chances.verified')} />
            </span>
            <span className="line-clamp-3 text-sm italic">“{src.quote}”</span>
          </button>
        ))}
      </div>
    </article>
  )
}

export function DischargePanel({ check }: { check: DischargeCheck }) {
  const { t } = useTranslation()
  const [source, setSource] = useState<ArgumentSource | null>(null)
  const clear = check.verdict === 'clear'

  return (
    <section className="flex flex-col gap-5">
      <header>
        <h2 className="font-display text-xl font-bold">{t('discharge.title')}</h2>
        <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <CheckCircle2Icon className="size-3.5 text-mint" aria-hidden />
          {t('chances.checked')}
        </p>
      </header>

      <div className="flex flex-col gap-2 border-y border-rule py-5">
        <p
          className={cn(
            'font-display text-3xl font-extrabold leading-none',
            clear ? 'text-mint' : check.verdict === 'high_risk' ? 'text-destructive' : 'text-amber',
          )}
        >
          {t(`discharge.verdict.${check.verdict}`, { defaultValue: check.verdict })}
        </p>
        <p className="max-w-[60ch] text-sm">{check.summary}</p>
      </div>

      {check.risks.length ? (
        <div className="flex flex-col gap-3">
          <h3 className="font-display text-base font-bold">{t('discharge.risks', { count: check.risks.length })}</h3>
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
