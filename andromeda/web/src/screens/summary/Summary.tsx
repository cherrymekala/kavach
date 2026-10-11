import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AppHeader, Badge, EmptyState, FileTile, FooterCTA } from '@/components'
import { useCase } from '@/api/hooks'
import { formatMoney } from '@/lib/money'
import { formatDate } from '@/lib/dates'

const CATEGORY_LABELS: Record<string, string> = {
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

export function Summary() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const facts = kase?.facts
  const currency = facts?.currency ?? (kase?.country === 'SG' ? 'SGD' : 'INR')

  if (!facts) {
    return (
      <div className="flex flex-col gap-6">
        <AppHeader title={t('summary.title')} />
        <EmptyState
          title={t('summary.notReady')}
          description={t('summary.notReadySub')}
          action={
            <button type="button" onClick={() => navigate(`/case/${caseId}/upload`)} className="text-brand underline">
              {t('upload.title')}
            </button>
          }
        />
      </div>
    )
  }

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

  return (
    <div className="flex flex-col gap-6">
      <AppHeader title={t('summary.title')} />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
            <h3 className="font-display text-base font-bold">{t('summary.reason')}</h3>
            <p className="text-balance">{facts.rejection_reason || t('summary.noReason')}</p>
            {facts.rejection_category ? (
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{CATEGORY_LABELS[facts.rejection_category] ?? facts.rejection_category}</Badge>
                {facts.rejection_code ? <Badge variant="outline">{facts.rejection_code}</Badge> : null}
              </div>
            ) : null}
            {facts.cited_clause ? (
              <p className="font-mono text-xs text-muted-foreground">{facts.cited_clause}</p>
            ) : null}
          </section>

          <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
            <h3 className="font-display text-base font-bold">{t('summary.amounts')}</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-muted-foreground">{t('summary.claimed')}</p>
                <p className="font-display text-xl font-extrabold">
                  {facts.claim_amount != null ? formatMoney(facts.claim_amount, currency) : '—'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('summary.approved')}</p>
                <p className="font-display text-xl font-extrabold">
                  {facts.amount_approved != null ? formatMoney(facts.amount_approved, currency) : '—'}
                </p>
              </div>
            </div>
          </section>
        </div>

        <div className="flex flex-col gap-6">
          {rows.length ? (
            <section className="flex flex-col gap-2 rounded-2xl border border-border bg-card p-5">
              <h3 className="font-display text-base font-bold">{t('summary.details')}</h3>
              <dl className="flex flex-col gap-2">
                {rows.map((r) => (
                  <div key={r.key} className="flex items-start justify-between gap-4 text-sm">
                    <dt className="shrink-0 text-muted-foreground">{r.key}</dt>
                    <dd className="min-w-0 break-words text-right font-medium">{r.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {dates.length ? (
            <section className="flex flex-col gap-2 rounded-2xl border border-border bg-card p-5">
              <h3 className="font-display text-base font-bold">{t('summary.timeline')}</h3>
              <dl className="flex flex-col gap-2">
                {dates.map((r) => (
                  <div key={r.key} className="flex items-start justify-between gap-4 text-sm">
                    <dt className="shrink-0 text-muted-foreground">{r.key}</dt>
                    <dd className="min-w-0 break-words text-right font-medium">{formatDate(r.value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {kase?.documents.some((d) => d.warning) ? (
            <section className="flex flex-col gap-2">
              <h3 className="font-display text-base font-bold">{t('summary.docs')}</h3>
              <div className="flex flex-col gap-2">
                {kase.documents
                  .filter((d) => d.warning)
                  .map((d) => (
                    <FileTile key={d.id} filename={d.filename} docType={d.doc_type} pages={d.pages} warning={d.warning} />
                  ))}
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <FooterCTA
        primary={{ label: t('summary.cta'), onClick: () => navigate(`/case/${caseId}/chances`) }}
      />
    </div>
  )
}