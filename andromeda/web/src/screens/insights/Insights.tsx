import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ShieldCheckIcon } from 'lucide-react'
import { useInsights } from '@/api/hooks'
import type { InsightRow } from '@/api/types'
import { cn } from '@/lib/cn'

type View = 'category' | 'insurer' | 'year'

/** One row: label, "patients won" bar on a muted track, percentage. Details on hover/focus. */
function Bar({ label, row }: { label: string; row: InsightRow }) {
  const { t } = useTranslation()
  const detail = t('insights.rowDetail', {
    total: row.total,
    allowed: row.allowed,
    partly: row.partly_allowed,
    dismissed: row.dismissed,
  })
  return (
    <li className="group grid grid-cols-[minmax(0,9rem)_1fr_3rem] items-center gap-3 py-1.5 sm:grid-cols-[14rem_1fr_3rem]" title={detail}>
      <span className="text-sm leading-tight">{label}</span>
      <span className="relative h-3 rounded-full bg-muted" aria-hidden>
        <span className="absolute inset-y-0 left-0 rounded-full bg-mint" style={{ width: `${row.won_pct}%` }} />
      </span>
      <span className="text-right font-mono text-sm font-semibold tabular-nums">{row.won_pct}%</span>
      <span className="col-span-3 hidden text-xs text-muted-foreground group-hover:block group-focus-within:block">
        {detail}
      </span>
    </li>
  )
}

export function Insights() {
  const { t } = useTranslation()
  const { data, isLoading, error } = useInsights('IN')
  const [view, setView] = useState<View>('category')

  if (isLoading) return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  if (error || !data) return <div className="py-16 text-center text-sm text-muted-foreground">{t('insights.unavailable')}</div>

  const rows = { category: data.by_category, insurer: data.by_insurer, year: data.by_year }[view]
  const label = (key: string) =>
    view === 'category' ? t(`summary.category.${key}`, { defaultValue: key.replace(/_/g, ' ') }) : key
  const best = data.by_category[0]
  const worst = data.by_category.at(-1)

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8">
      <header className="flex items-center gap-2.5">
        <span className="grid size-8 place-items-center rounded-lg bg-brand text-primary-foreground">
          <ShieldCheckIcon className="size-5" aria-hidden />
        </span>
        <Link to="/" className="font-display text-lg font-bold">
          Kavach
        </Link>
        <span className="ml-auto text-xs text-muted-foreground">{t('insights.kicker')}</span>
      </header>

      <section className="flex flex-col gap-2">
        <h1 className="font-display text-2xl font-extrabold text-balance">{t('insights.title')}</h1>
        <p className="text-sm text-muted-foreground">
          {t('insights.sub', { total: data.overall.total.toLocaleString('en-IN'), from: data.period.from, to: data.period.to })}
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl bg-primary p-5 text-primary-foreground">
          <p className="font-display text-4xl font-extrabold">{data.overall.won_pct}%</p>
          <p className="text-sm opacity-85">{t('insights.overall')}</p>
        </div>
        {best ? (
          <div className="rounded-2xl border border-border bg-card p-5">
            <p className="font-display text-4xl font-extrabold">{best.won_pct}%</p>
            <p className="text-sm text-muted-foreground">{t('insights.best', { ground: label(best.key) })}</p>
          </div>
        ) : null}
        {worst ? (
          <div className="rounded-2xl border border-border bg-card p-5">
            <p className="font-display text-4xl font-extrabold">{worst.won_pct}%</p>
            <p className="text-sm text-muted-foreground">{t('insights.worst', { ground: label(worst.key) })}</p>
          </div>
        ) : null}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-base font-bold">{t('insights.chartTitle')}</h2>
          <div role="tablist" className="flex rounded-full bg-muted p-1 text-sm">
            {(['category', 'insurer', 'year'] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="tab"
                aria-selected={view === v}
                onClick={() => setView(v)}
                className={cn('h-9 rounded-full px-3', view === v ? 'bg-card font-semibold shadow-sm' : 'text-muted-foreground')}
              >
                {t(`insights.by.${v}`)}
              </button>
            ))}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{t('insights.won')}</p>
        <ul className="flex flex-col">
          {rows.map((r) => (
            <Bar key={r.key} label={label(r.key)} row={r} />
          ))}
        </ul>
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-brand">{t('insights.table')}</summary>
          <table className="mt-3 w-full text-left font-mono text-xs tabular-nums">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-1 font-normal">{t(`insights.by.${view}`)}</th>
                <th className="py-1 text-right font-normal">{t('insights.col.total')}</th>
                <th className="py-1 text-right font-normal">{t('insights.col.allowed')}</th>
                <th className="py-1 text-right font-normal">{t('insights.col.partly')}</th>
                <th className="py-1 text-right font-normal">{t('insights.col.dismissed')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-t border-border">
                  <td className="py-1 font-sans">{label(r.key)}</td>
                  <td className="py-1 text-right">{r.total}</td>
                  <td className="py-1 text-right">{r.allowed}</td>
                  <td className="py-1 text-right">{r.partly_allowed}</td>
                  <td className="py-1 text-right">{r.dismissed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>

      <p className="text-xs text-muted-foreground">
        {data.source}. {data.note}
      </p>
    </div>
  )
}
