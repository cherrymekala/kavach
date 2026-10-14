import { useTranslation } from 'react-i18next'
import { Badge, FileTile } from '@/components'
import type { Case } from '@/api/types'
import { formatDate } from '@/lib/dates'
import { formatMoney } from '@/lib/money'
import { currencyFor } from '@/lib/country'

const CATEGORY: Record<string, string> = {
  pre_existing: 'Pre-existing condition',
  specific_waiting_period: 'Specific waiting period',
  initial_waiting_period: 'Initial waiting period',
  non_disclosure: 'Non-disclosure',
  room_rent: 'Room rent',
  reasonable_charges: 'Reasonable charges',
  diagnostic_only: 'Diagnostic only',
  not_medically_necessary: 'Not medically necessary',
  excluded_treatment: 'Excluded treatment',
  missing_documents: 'Missing documents',
  late_intimation: 'Late intimation',
  sub_limit: 'Sub-limit',
  under_24_hours: 'Under 24 hours',
  hospital_ineligible: 'Hospital not eligible',
  duplicate_claim: 'Duplicate claim',
  fraud: 'Fraud',
  other: 'Other',
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-rule/60 py-2 last:border-0">
      <dt className="shrink-0 text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-right text-sm font-medium">{value}</dd>
    </div>
  )
}

export function SummaryPanel({ kase }: { kase: Case }) {
  const { t } = useTranslation()
  const facts = kase.facts
  if (!facts) return null

  const currency = facts.currency ?? currencyFor(kase.country)

  const rows = [
    { key: t('summary.patient'), value: facts.patient_name },
    { key: t('summary.insurer'), value: facts.insurer },
    { key: t('summary.hospital'), value: facts.hospital },
    { key: t('summary.policy'), value: facts.policy_number },
    { key: t('summary.claimNumber'), value: facts.claim_number },
  ].filter((r): r is { key: string; value: string } => Boolean(r.value))

  const dates = [
    { key: t('summary.admission'), value: facts.admission_date },
    { key: t('summary.rejectionDate'), value: facts.rejection_date },
    { key: t('summary.policyStart'), value: facts.policy_start },
    { key: t('summary.diagnosisDate'), value: facts.first_diagnosis_date },
  ].filter((r): r is { key: string; value: string } => Boolean(r.value))

  const warnings = (kase.documents ?? []).filter((d) => d.warning)

  return (
    <section className="flex flex-col gap-6">
      <p className="max-w-[62ch] text-[17px] leading-relaxed">
        {facts.rejection_reason || t('summary.noReason')}
      </p>

      {facts.rejection_category ? (
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{CATEGORY[facts.rejection_category] ?? facts.rejection_category}</Badge>
          {facts.rejection_code ? <Badge variant="outline">{facts.rejection_code}</Badge> : null}
          {facts.cited_clause ? (
            <span className="font-mono text-xs text-muted-foreground">{facts.cited_clause}</span>
          ) : null}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-8 border-y border-rule py-4">
        <div>
          <p className="text-sm text-muted-foreground">{t('summary.claimed')}</p>
          <p className="font-display text-2xl font-extrabold tabular-nums">
            {facts.claim_amount != null ? formatMoney(facts.claim_amount, currency) : '—'}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{t('summary.approved')}</p>
          <p className="font-display text-2xl font-extrabold tabular-nums">
            {facts.amount_approved != null ? formatMoney(facts.amount_approved, currency) : '—'}
          </p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {rows.length ? (
          <dl className="flex flex-col">
            {rows.map((r) => (
              <Row key={r.key} label={r.key} value={r.value} />
            ))}
          </dl>
        ) : null}

        {dates.length ? (
          <dl className="flex flex-col">
            {dates.map((r) => (
              <Row key={r.key} label={r.key} value={formatDate(r.value)} />
            ))}
          </dl>
        ) : null}
      </div>

      {warnings.length ? (
        <div className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('summary.docs')}</h3>
          <div className="flex flex-col gap-2">
            {warnings.map((d) => (
              <FileTile key={d.id} filename={d.filename} docType={d.doc_type} pages={d.pages} warning={d.warning} />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}