import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRightIcon, PlusIcon } from 'lucide-react'
import { AppHeader, Badge, Button, Countdown, Spinner } from '@/components'
import { useCases } from '@/api/hooks'
import type { CaseSummary } from '@/api/types'
import { formatDate } from '@/lib/dates'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/cn'

/** Where to resume a case, based on how far it got. */
function resumePath(c: CaseSummary): string {
  switch (c.status) {
    case 'ready':
      return `/case/${c.id}/summary`
    case 'filed':
    case 'escalated':
      return `/case/${c.id}/tracker`
    case 'resolved':
      return `/case/${c.id}/outcome`
    default:
      return `/case/${c.id}/upload`
  }
}

const STRENGTH_TONE: Record<string, string> = {
  strong: 'text-mint',
  medium: 'text-amber',
  weak: 'text-muted-foreground',
}

export function MyCases() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data, isLoading, error } = useCases()

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    )
  }
  if (!error && data && data.length === 0) return <Navigate to="/start" replace />

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <AppHeader title={t('cases.title')} />
      {error ? <p className="text-sm text-destructive">{error.message}</p> : null}
      <ul className="flex flex-col gap-2">
        {data?.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => navigate(resumePath(c))}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-card p-4 text-left hover:bg-accent/40"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-semibold">{c.insurer ?? t('cases.untitled')}</span>
                  <Badge variant="secondary">{t(`cases.status.${c.status}`)}</Badge>
                </div>
                <span className="truncate text-sm text-muted-foreground">
                  {[c.diagnosis, c.claim_amount != null && c.currency ? formatMoney(c.claim_amount, c.currency) : null]
                    .filter(Boolean)
                    .join(' · ') || t('cases.noDetails')}
                </span>
                <span className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
                  <span>{c.country}</span>
                  {c.created_at ? <span>{formatDate(c.created_at)}</span> : null}
                  {c.strength ? (
                    <span className={cn('font-semibold', STRENGTH_TONE[c.strength])}>
                      {t(`cases.strength.${c.strength}`)}
                    </span>
                  ) : null}
                  {c.status === 'analysing' && c.progress ? <span>{c.progress}</span> : null}
                  <Countdown deadline={c.next_deadline} />
                </span>
              </div>
              <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
      <Button variant="outline" onClick={() => navigate('/start')}>
        <PlusIcon className="size-4" aria-hidden />
        {t('cases.new')}
      </Button>
    </div>
  )
}
