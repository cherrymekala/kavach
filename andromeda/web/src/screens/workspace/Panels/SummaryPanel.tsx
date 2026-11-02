import { useTranslation } from 'react-i18next'
import { ArrowRightIcon } from 'lucide-react'
import { Button, FileTile, ShieldHero } from '@/components'
import type { Case } from '@/api/types'
import { formatDate } from '@/lib/dates'
import { formatMoney } from '@/lib/money'
import { currencyFor } from '@/lib/country'
import { cn } from '@/lib/cn'
import { shortInsurer } from '@/lib/insurer'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-rule/60 py-2.5 last:border-0">
      <dt className="shrink-0 text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-right text-sm font-medium break-words">{value}</dd>
    </div>
  )
}

export function SummaryPanel({ kase, onNext }: { kase: Case; onNext?: () => void }) {
  const { t } = useTranslation()
  const facts = kase.facts
  if (!facts) return null

  const currency = facts.currency ?? currencyFor(kase.country)
  const insurer = facts.insurer ? shortInsurer(facts.insurer) : t('summary.yourInsurer')
  const claimed = facts.claim_amount != null ? formatMoney(facts.claim_amount, currency) : null
  const approved = facts.amount_approved ? formatMoney(facts.amount_approved, currency) : null
  const headline =
    claimed && approved
      ? t('summary.headlinePartial', { insurer, approved, claimed })
      : claimed
        ? t('summary.headline', { insurer, amount: claimed })
        : t('summary.headlineNoAmount', { insurer })
  const category = facts.rejection_category
  const meaning = category ? t(`summary.meaning.${category}`, { defaultValue: '' }) : ''
  const unpaid =
    facts.claim_amount != null ? Math.max(0, facts.claim_amount - (facts.amount_approved ?? 0)) : null

  const rows = [
    { key: t('summary.patient'), value: facts.patient_name },
    { key: t('summary.insurer'), value: facts.insurer },
    { key: t('summary.hospital'), value: facts.hospital },
    { key: t('summary.policy'), value: facts.policy_number },
    { key: t('summary.claimNumber'), value: facts.claim_number },
  ].filter((r): r is { key: string; value: string } => Boolean(r.value))

  // Oldest first, so the patient reads the story in order.
  const timeline = [
    { key: t('summary.policyStart'), value: facts.policy_start },
    { key: t('summary.diagnosisDate'), value: facts.first_diagnosis_date },
    { key: t('summary.admission'), value: facts.admission_date },
    { key: t('summary.rejectionDate'), value: facts.rejection_date, hot: true },
  ]
    .filter((r): r is { key: string; value: string; hot?: boolean } => Boolean(r.value))
    .sort((a, b) => a.value.localeCompare(b.value))

  const warnings = (kase.documents ?? []).filter((d) => d.warning)

  return (
    <section className="flex flex-col gap-10">
      <ShieldHero
        eyebrow={t('summary.title')}
        footer={category ? t(`summary.category.${category}`, { defaultValue: category }) : undefined}
      >
        {headline}
      </ShieldHero>

      <div className="flex flex-col gap-3">
        <h3 className="text-xl font-extrabold tracking-tight">{t('summary.reason')}</h3>
        <blockquote className="rounded-2xl bg-muted/70 p-4 text-[15px] leading-relaxed">
          “{facts.rejection_reason || t('summary.noReason')}”
          {facts.cited_clause || facts.rejection_code ? (
            <span className="mt-2 block text-xs text-muted-foreground">
              {[facts.rejection_code, facts.cited_clause].filter(Boolean).join(' · ')}
            </span>
          ) : null}
        </blockquote>
      </div>

      {meaning ? (
        <div className="flex flex-col gap-2">
          <h3 className="text-xl font-extrabold tracking-tight">{t('summary.whatItMeans')}</h3>
          <p className="max-w-[62ch] text-[15px] leading-relaxed">{meaning}</p>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border">
        <div className="flex flex-col gap-1 bg-background p-4">
          <p className="text-sm text-muted-foreground">{t('summary.claimed')}</p>
          <p className="text-2xl font-extrabold tracking-tight tabular-nums">{claimed ?? '—'}</p>
        </div>
        <div className="flex flex-col gap-1 bg-background p-4">
          <p className="text-sm text-muted-foreground">{t('summary.approved')}</p>
          <p className="text-2xl font-extrabold tracking-tight tabular-nums">
            {facts.amount_approved != null ? formatMoney(facts.amount_approved, currency) : '—'}
          </p>
        </div>
        {unpaid ? (
          <p className="col-span-2 bg-background px-4 py-3 text-sm font-semibold text-destructive">
            {t('summary.unpaid', { amount: formatMoney(unpaid, currency) })}
          </p>
        ) : null}
      </div>

      {timeline.length ? (
        <div className="flex flex-col gap-4">
          <h3 className="text-xl font-extrabold tracking-tight">{t('summary.timeline')}</h3>
          <ol className="flex flex-col">
            {timeline.map((r, i) => (
              <li key={r.key} className="relative flex items-baseline justify-between gap-4 pb-5 pl-6 last:pb-0">
                {i < timeline.length - 1 ? (
                  <span className="absolute top-2 bottom-0 left-[5px] w-px bg-rule" aria-hidden />
                ) : null}
                <span
                  className={cn(
                    'absolute top-1.5 left-0 size-[11px] rounded-full border-2',
                    r.hot ? 'border-destructive bg-destructive' : 'border-brand bg-background',
                  )}
                  aria-hidden
                />
                <span className={cn('text-sm', r.hot && 'font-semibold')}>{r.key}</span>
                <span className="text-sm font-semibold tabular-nums">{formatDate(r.value)}</span>
              </li>
            ))}
          </ol>
          {!facts.policy_start ? (
            <p className="max-w-[62ch] rounded-2xl border border-amber/40 bg-amber/10 p-4 text-sm leading-relaxed">
              {t('summary.missing.policyStart')}
            </p>
          ) : null}
        </div>
      ) : null}

      {rows.length ? (
        <div className="flex flex-col gap-2">
          <h3 className="text-xl font-extrabold tracking-tight">{t('summary.details')}</h3>
          <dl className="flex flex-col">
            {rows.map((r) => (
              <Row key={r.key} label={r.key} value={r.value} />
            ))}
          </dl>
        </div>
      ) : null}

      {warnings.length ? (
        <div className="flex flex-col gap-2">
          <h3 className="text-xl font-extrabold tracking-tight">{t('summary.check')}</h3>
          <div className="flex flex-col gap-2">
            {warnings.map((d) => (
              <FileTile key={d.id} filename={d.filename} docType={d.doc_type} pages={d.pages} warning={d.warning} />
            ))}
          </div>
        </div>
      ) : null}

      {onNext ? (
        <Button size="lg" onClick={onNext} className="h-12 w-full rounded-full text-base sm:w-auto sm:self-start sm:px-8">
          {t('summary.cta')}
          <ArrowRightIcon aria-hidden />
        </Button>
      ) : null}
    </section>
  )
}
