import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangleIcon, CheckCircle2Icon, QuoteIcon } from 'lucide-react'
import { AppHeader, Badge, EmptyState, FooterCTA, SourceKindIcon } from '@/components'
import { useCase } from '@/api/hooks'
import { formatMoney } from '@/lib/money'
import { formatDate } from '@/lib/dates'
import { cn } from '@/lib/cn'

/** Insurer names often arrive in capitals from letterheads. */
function tidy(name: string): string {
  if (name !== name.toUpperCase()) return name
  return name
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\b(Co|Ltd|Pvt)\b\.?/g, (m) => m)
}

function shortInsurer(name: string): string {
  return tidy(name)
    .replace(/\b(and Allied|Insurance|Company|Co\.?|Limited|Ltd\.?|Private|Pvt\.?|General)\b/gi, '')
    .replace(/[\s.,&]+$/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

interface Milestone {
  key: string
  date: string | null | undefined
  important?: boolean
}

export function Summary() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const facts = kase?.facts
  if (!facts) {
    return (
      <div className="flex flex-col gap-6">
        <AppHeader title={t('summary.title')} />
        <EmptyState
          title={t('summary.notReady')}
          description={t('summary.notReadySub')}
          action={
            <button type="button" onClick={() => navigate(`/case/${caseId}/upload`)} className="text-brand underline">
              {t('upload.heading')}
            </button>
          }
        />
      </div>
    )
  }

  const currency = facts.currency ?? (kase?.country === 'SG' ? 'SGD' : 'INR')
  const money = (n: number | null | undefined) => (n != null ? formatMoney(n, currency) : null)
  const insurer = facts.insurer ? shortInsurer(facts.insurer) : t('summary.yourInsurer')
  const claimed = money(facts.claim_amount)
  const partial = facts.amount_approved != null && facts.amount_approved > 0

  const headline = partial
    ? t('summary.headlinePartial', { insurer, approved: money(facts.amount_approved), claimed })
    : claimed
      ? t('summary.headline', { insurer, amount: claimed })
      : t('summary.headlineNoAmount', { insurer })
  const context = [facts.diagnosis, facts.hospital, facts.admission_date ? formatDate(facts.admission_date) : null]
    .filter(Boolean)
    .join(' · ')

  const category = facts.rejection_category
  const meaning = category ? t(`summary.meaning.${category}`, { defaultValue: '' }) : ''

  // Policy start matters for waiting periods and pre-existing conditions, so show it even when missing.
  const milestones: Milestone[] = [
    { key: 'policyStart', date: facts.policy_start, important: true },
    { key: 'diagnosisDate', date: facts.first_diagnosis_date },
    { key: 'admission', date: facts.admission_date },
    { key: 'rejectionDate', date: facts.rejection_date },
  ]
  const known = milestones.filter((m) => m.date).sort((a, b) => String(a.date).localeCompare(String(b.date)))
  const missing = milestones.filter((m) => !m.date && m.important)

  const details = [
    { key: t('summary.patient'), value: facts.patient_name },
    { key: t('summary.insurer'), value: facts.insurer ? tidy(facts.insurer) : null },
    { key: t('summary.policy'), value: facts.policy_number },
    { key: t('summary.claimNumber'), value: facts.claim_number },
  ].filter((r): r is { key: string; value: string } => Boolean(r.value))

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-24">
      <AppHeader title={t('summary.title')} />

      <section className="flex flex-col gap-2 rounded-2xl bg-primary p-5 text-primary-foreground">
        <p className="font-display text-2xl font-extrabold leading-tight text-balance">{headline}</p>
        {context ? <p className="text-sm opacity-85">{context}</p> : null}
        {partial ? (
          <p className="mt-1 font-mono text-sm">
            {t('summary.unpaid', { amount: money((facts.claim_amount ?? 0) - (facts.amount_approved ?? 0)) })}
          </p>
        ) : null}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h3 className="font-display text-base font-bold">{t('summary.reason')}</h3>
        {facts.rejection_reason ? (
          <p className="flex gap-2 text-balance">
            <QuoteIcon className="mt-1 size-4 shrink-0 text-muted-foreground" aria-hidden />
            <span>{facts.rejection_reason}</span>
          </p>
        ) : (
          <p className="text-muted-foreground">{t('summary.noReason')}</p>
        )}
        {category || facts.cited_clause || facts.rejection_code ? (
          <div className="flex flex-wrap gap-2">
            {category ? <Badge variant="secondary">{t(`summary.category.${category}`, { defaultValue: category })}</Badge> : null}
            {facts.cited_clause ? (
              <Badge variant="outline" className="h-auto max-w-full whitespace-normal text-left font-mono">
                {facts.cited_clause}
              </Badge>
            ) : null}
            {facts.rejection_code ? <Badge variant="outline" className="font-mono">{facts.rejection_code}</Badge> : null}
          </div>
        ) : null}
        {meaning ? (
          <div className="rounded-lg bg-accent/60 p-3 text-sm">
            <p className="font-semibold">{t('summary.whatItMeans')}</p>
            <p className="text-muted-foreground">{meaning}</p>
          </div>
        ) : null}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h3 className="font-display text-base font-bold">{t('summary.timeline')}</h3>
        <ol className="flex flex-col">
          {known.map((m, i) => (
            <li key={m.key} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className={cn('mt-1.5 size-3 rounded-full', m.key === 'rejectionDate' ? 'bg-destructive' : 'bg-brand')} />
                {i < known.length - 1 ? <span className="my-1 w-0.5 flex-1 bg-border" /> : null}
              </div>
              <div className="flex flex-1 items-baseline justify-between gap-3 pb-4">
                <span className="text-sm">{t(`summary.${m.key}`)}</span>
                <span className="font-mono text-sm font-semibold tabular-nums">{formatDate(m.date)}</span>
              </div>
            </li>
          ))}
        </ol>
        {missing.map((m) => (
          <p key={m.key} className="flex gap-2 rounded-lg border border-amber/40 bg-amber/10 p-3 text-sm">
            <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-amber" aria-hidden />
            <span>{t(`summary.missing.${m.key}`)}</span>
          </p>
        ))}
      </section>

      {kase?.documents.length ? (
        <section className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('summary.docs')}</h3>
          <ul className="flex flex-col gap-2">
            {kase.documents.map((d) => (
              <li key={d.id} className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
                <SourceKindIcon kind={d.doc_type ?? 'other'} className="size-5 text-brand" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{t(`chances.kind.${d.doc_type ?? 'other'}`)}</p>
                  <p className="truncate text-xs text-muted-foreground">{d.warning ?? d.filename}</p>
                </div>
                {d.warning ? (
                  <AlertTriangleIcon className="size-4 shrink-0 text-amber" aria-label={t('summary.check')} />
                ) : (
                  <CheckCircle2Icon className="size-4 shrink-0 text-mint" aria-label={t('summary.read')} />
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {details.length ? (
        <details className="rounded-2xl border border-border bg-card p-5">
          <summary className="cursor-pointer font-display text-base font-bold">{t('summary.details')}</summary>
          <dl className="mt-3 flex flex-col gap-2">
            {details.map((r) => (
              <div key={r.key} className="flex items-start justify-between gap-4 text-sm">
                <dt className="shrink-0 text-muted-foreground">{r.key}</dt>
                <dd className="min-w-0 break-words text-right font-mono">{r.value}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}

      <FooterCTA primary={{ label: t('summary.cta'), onClick: () => navigate(`/case/${caseId}/chances`) }} />
    </div>
  )
}
