import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BadgeCheckIcon, ChevronDownIcon, CircleIcon, CheckCircle2Icon, ShieldCheckIcon } from 'lucide-react'
import { AppHeader, EmptyState, FooterCTA, SourceKindIcon } from '@/components'
import type { ArgumentSource } from '@/components'
import { useCase, usePack } from '@/api/hooks'
import type { Argument } from '@/api/types'
import { cn } from '@/lib/cn'
import { SourceSheet } from './SourceSheet'

const LEVELS = ['weak', 'medium', 'strong'] as const
const LEVEL_TONE: Record<string, string> = { strong: 'bg-mint', medium: 'bg-amber', weak: 'bg-muted-foreground' }
const LEVEL_TEXT: Record<string, string> = { strong: 'text-mint', medium: 'text-amber', weak: 'text-muted-foreground' }

/** Our citations carry file names for uploaded documents; show the kind of document instead. */
function isFileName(ref: string): boolean {
  return /\.(txt|pdf|jpe?g|png|webp)$/i.test(ref)
}

function Verdict({ strength }: { strength: string }) {
  const { t } = useTranslation()
  const level = Math.max(0, LEVELS.indexOf(strength as (typeof LEVELS)[number]))
  return (
    <div className="flex flex-col gap-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t('chances.verdict')}
      </span>
      <p className={cn('font-display text-3xl font-extrabold leading-none', LEVEL_TEXT[strength])}>
        {t(`chances.strength.${strength}`)}
      </p>
      <div className="grid grid-cols-3 gap-1.5" aria-hidden>
        {LEVELS.map((l, i) => (
          <span key={l} className={cn('h-2 rounded-full', i <= level ? LEVEL_TONE[strength] : 'bg-muted')} />
        ))}
      </div>
      <p className="text-sm text-muted-foreground">{t(`chances.strengthHint.${strength}`)}</p>
    </div>
  )
}

function Precedents({ won, total, body }: { won: number; total: number; body: string }) {
  const { t } = useTranslation()
  if (!total) return null
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-4">
      <p className="text-sm">
        <span className="font-display text-xl font-extrabold">
          {won}/{total}
        </span>{' '}
        <span className="text-muted-foreground">{t('chances.precedents', { body })}</span>
      </p>
      <div className="flex flex-wrap gap-1.5" role="img" aria-label={t('chances.won', { won, total })}>
        {Array.from({ length: total }, (_, i) => (
          <span key={i} className={cn('size-3.5 rounded-full', i < won ? 'bg-mint' : 'bg-muted')} />
        ))}
      </div>
    </div>
  )
}

function Evidence({ source, onOpen }: { source: ArgumentSource; onOpen: () => void }) {
  const { t } = useTranslation()
  const kind = source.kind ?? 'other'
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full flex-col gap-1.5 rounded-lg bg-muted/60 p-3 text-left hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <span className="flex items-center gap-1.5 text-xs font-semibold text-brand">
        <SourceKindIcon kind={kind} className="size-3.5" />
        <span className="shrink-0">{t(`chances.kind.${kind}`, { defaultValue: kind })}</span>
        {!isFileName(source.ref) ? (
          <span className="min-w-0 truncate font-normal text-muted-foreground">· {source.ref}</span>
        ) : null}
        <BadgeCheckIcon className="ml-auto size-3.5 shrink-0 text-mint" aria-label={t('chances.verified')} />
      </span>
      {source.quote ? <span className="line-clamp-3 text-sm italic">“{source.quote}”</span> : null}
    </button>
  )
}

function ArgumentCard({
  index,
  argument,
  onSource,
}: {
  index: number
  argument: Argument
  onSource: (s: ArgumentSource) => void
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4">
      <div className="flex gap-3">
        <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary font-display text-sm font-bold text-primary-foreground">
          {index + 1}
        </span>
        <p className="font-semibold leading-snug">{argument.claim}</p>
      </div>
      <div className="flex flex-col gap-2">
        {argument.sources.map((s, i) => (
          <Evidence
            key={`${s.ref}-${i}`}
            source={{ ref: s.ref, quote: s.quote, kind: s.kind }}
            onOpen={() => onSource({ ref: s.ref, quote: s.quote, kind: s.kind })}
          />
        ))}
      </div>
      {argument.explanation ? (
        <div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1 text-sm font-semibold text-brand"
            aria-expanded={open}
          >
            {t('chances.why')}
            <ChevronDownIcon className={cn('size-4 transition-transform', open && 'rotate-180')} aria-hidden />
          </button>
          {open ? <p className="mt-2 text-sm text-muted-foreground">{argument.explanation}</p> : null}
        </div>
      ) : null}
    </article>
  )
}

export function Chances() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const { data: pack } = usePack(kase?.country)
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
            <button type="button" onClick={() => navigate(`/case/${caseId}/summary`)} className="text-brand underline">
              {t('summary.title')}
            </button>
          }
        />
      </div>
    )
  }

  const args = assessment.arguments ?? []
  const missing = assessment.missing_documents ?? []
  const body = pack?.ladder.at(-1)?.step ?? t('chances.disputeBody')

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-24">
      <AppHeader title={t('chances.title')} />

      <section className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
        <Verdict strength={assessment.strength} />
        <Precedents won={assessment.similar_cases_won ?? 0} total={assessment.similar_cases_total ?? 0} body={body} />
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="font-display text-base font-bold">{t('chances.arguments', { count: args.length })}</h3>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <ShieldCheckIcon className="size-3.5 text-mint" aria-hidden />
            {t('chances.checked')}
          </span>
        </div>
        {args.length ? (
          args.map((a, i) => <ArgumentCard key={`${i}-${a.claim}`} index={i} argument={a} onSource={setSource} />)
        ) : (
          <p className="text-sm text-muted-foreground">{t('chances.noArguments')}</p>
        )}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h3 className="font-display text-base font-bold">{t('chances.missing')}</h3>
        {missing.length ? (
          <ul className="flex flex-col gap-3">
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

      <FooterCTA primary={{ label: t('chances.cta'), onClick: () => navigate(`/case/${caseId}/letter`) }} />
      <SourceSheet source={source} onClose={() => setSource(null)} />
    </div>
  )
}
