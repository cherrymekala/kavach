import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRightIcon, CheckIcon, Share2Icon } from 'lucide-react'
import { Button, KavachMark } from '@/components'
import { useInsights, useScorecard } from '@/api/hooks'

/**
 * Public, shareable scorecard for one insurer, from published Insurance Ombudsman awards:
 * how patients fared, on which grounds, against the average across all insurers. Factual
 * framing only (no rankings), with the data's limits stated next to the numbers.
 */
export function Scorecard() {
  const { slug } = useParams()
  const { t } = useTranslation()
  const { data: card, isLoading, error } = useScorecard('IN', slug)
  const { data: report } = useInsights('IN')
  const [copied, setCopied] = useState(false)

  if (isLoading) return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  if (error || !card) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">{t('scorecard.missing')}</p>
        <Link to="/insights" className="text-sm font-semibold text-brand underline">
          {t('scorecard.back')}
        </Link>
      </div>
    )
  }

  const everyone = report?.overall.won_pct
  const diff = everyone != null ? card.won_pct - everyone : null

  async function share() {
    const url = window.location.href
    const title = t('scorecard.shareTitle', { insurer: card!.key })
    try {
      if (navigator.share) await navigator.share({ title, url })
      else {
        await navigator.clipboard.writeText(url)
        setCopied(true)
        window.setTimeout(() => setCopied(false), 2000)
      }
    } catch {
      /* the patient closed the share sheet */
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-8">
      <header className="flex items-center gap-2">
        <KavachMark className="h-7 text-ink" />
        <Link to="/insights" className="font-display text-lg font-extrabold tracking-[-0.05em]">
          kavach
        </Link>
        <Link to="/insights" className="ml-auto text-xs font-semibold text-brand">
          {t('scorecard.back')}
        </Link>
      </header>

      <section className="animate-rise flex flex-col gap-4 rounded-[28px] bg-card p-6 shadow-[0_18px_40px_rgb(46_31_184/0.08)]">
        <span className="w-fit rounded-full bg-accent px-3 py-1 text-xs font-bold text-accent-foreground">{t('scorecard.kicker')}</span>
        <h1 className="font-display text-[1.9rem] leading-tight font-bold tracking-[-0.03em]">{card.key}</h1>
        {card.now_known_as ? <p className="-mt-2 text-sm text-muted-foreground">{t('scorecard.nowKnownAs', { name: card.now_known_as })}</p> : null}
        <p className="flex flex-col gap-2">
          <span className="font-display text-6xl leading-none font-bold tabular-nums">{card.won_pct}%</span>
          <span className="max-w-[48ch] text-sm text-muted-foreground">
            {t('scorecard.headline', { total: card.total, from: card.period?.from, to: card.period?.to })}
          </span>
        </p>
        {everyone != null && diff != null ? (
          <p className="text-sm">
            {t('scorecard.everyone', { pct: everyone })}{' '}
            <span className="font-semibold">
              {diff === 0 ? t('scorecard.same') : t(diff > 0 ? 'scorecard.higher' : 'scorecard.lower', { points: Math.abs(diff) })}
            </span>
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={share}>
            {copied ? <CheckIcon className="text-mint" aria-hidden /> : <Share2Icon aria-hidden />}
            {copied ? t('scorecard.copied') : t('scorecard.share')}
          </Button>
        </div>
      </section>

      {card.grounds?.length ? (
        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-extrabold tracking-tight">{t('scorecard.grounds')}</h2>
          <ul className="flex flex-col gap-2">
            {card.grounds.map((g) => (
              <li key={g.key} className="flex flex-col gap-2 rounded-[22px] bg-card p-4">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-bold">{t(`summary.category.${g.key}`, { defaultValue: g.key.replace(/_/g, ' ') })}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{t('scorecard.share_of', { pct: g.share_pct, count: g.total })}</span>
                </div>
                <span className="relative h-2.5 rounded-full bg-muted" aria-hidden>
                  <span className="absolute inset-y-0 left-0 rounded-full bg-brand" style={{ width: `${g.won_pct}%` }} />
                </span>
                <p className="text-sm">
                  {t('scorecard.groundWon', { pct: g.won_pct })}
                  {g.everyone_won_pct != null ? <span className="text-muted-foreground"> · {t('scorecard.groundEveryone', { pct: g.everyone_won_pct })}</span> : null}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {card.by_year && card.by_year.length > 1 ? (
        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-extrabold tracking-tight">{t('scorecard.years')}</h2>
          <ol className="flex items-end gap-1.5 rounded-[22px] bg-card p-4" aria-label={t('scorecard.years')}>
            {card.by_year.map((y) => (
              <li key={y.key} className="flex flex-1 flex-col items-center gap-1" title={t('scorecard.yearDetail', { pct: y.won_pct, count: y.total })}>
                <span className="text-[11px] font-semibold tabular-nums">{y.won_pct}%</span>
                <span className="w-full rounded-t-md bg-brand/80" style={{ height: `${Math.max(6, y.won_pct)}px` }} aria-hidden />
                <span className="text-[11px] text-muted-foreground">{y.key}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section className="flex flex-col gap-2 rounded-[22px] border border-border p-5 text-sm">
        <h2 className="font-bold">{t('scorecard.aboutTitle')}</h2>
        <p className="text-muted-foreground">{t('scorecard.about')}</p>
        {report ? <p className="text-xs text-muted-foreground">{report.source}.</p> : null}
      </section>

      <Link
        to="/"
        className="flex items-center justify-between gap-3 rounded-[24px] bg-primary p-5 text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <span className="font-bold">{t('scorecard.cta', { insurer: card.key })}</span>
        <ArrowRightIcon className="size-5 shrink-0" aria-hidden />
      </Link>
    </div>
  )
}
