import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckCircle2Icon, CircleIcon } from 'lucide-react'
import { AppHeader, Argument, EmptyState, FooterCTA, Meter } from '@/components'
import { useCase } from '@/api/hooks'
import type { ArgumentSource } from '@/components'
import { SourceSheet } from './SourceSheet'

export function Chances() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const [source, setSource] = useState<ArgumentSource | null>(null)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const assessment = kase?.assessment

  if (!assessment) {
    return (
      <div className="flex flex-col gap-6">
        <AppHeader title={t('chances.title')} />
        <EmptyState
          title={t('chances.notReady')}
          description={t('chances.notReadySub')}
          action={
            <button
              type="button"
              onClick={() => navigate(`/case/${caseId}/summary`)}
              className="text-brand underline"
            >
              {t('summary.title')}
            </button>
          }
        />
      </div>
    )
  }

  const score = Math.max(0, Math.min(1, assessment.score))
  const strength = assessment.strength
  const tone = strength === 'strong' ? 'mint' : 'amber'

  const args = assessment.arguments ?? []
  const missing = assessment.missing_documents ?? []

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <AppHeader title={t('chances.title')} />

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <div className="flex items-end justify-between">
          <h3 className="font-display text-base font-bold">{t('chances.score')}</h3>
          <span className="font-display text-2xl font-extrabold text-brand">{Math.round(score * 100)}%</span>
        </div>
        <Meter value={score} tone={tone} />
        <p className="text-sm font-semibold">{t(`chances.strength.${strength}`)}</p>
        <p className="text-sm text-muted-foreground">
          {t('chances.won', {
            won: assessment.similar_cases_won ?? 0,
            total: assessment.similar_cases_total ?? 0,
          })}
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="font-display text-base font-bold">{t('chances.arguments')}</h3>
        <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
          {args.length ? (
            args.map((a) => (
              <Argument
                key={a.claim}
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
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h3 className="font-display text-base font-bold">{t('chances.missing')}</h3>
        {missing.length ? (
          <ul className="flex flex-col gap-2">
            {missing.map((m) => (
              <li key={m} className="flex items-start gap-2 text-sm">
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
      </section>

      <p className="text-xs text-muted-foreground">{assessment.disclaimer}</p>

      <FooterCTA
        primary={{ label: t('chances.cta'), onClick: () => navigate(`/case/${caseId}/letter`) }}
      />

      <SourceSheet source={source} onClose={() => setSource(null)} />
    </div>
  )
}