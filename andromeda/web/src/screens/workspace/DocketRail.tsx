import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MenuIcon, PlusIcon, ShieldCheckIcon } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { useCases } from '@/api/hooks'
import type { CaseSummary } from '@/api/types'
import { formatMoney } from '@/lib/money'
import { timeAgo } from '@/lib/dates'
import { cn } from '@/lib/cn'
import { AccountStrip } from './AccountStrip'

const DOT: Record<string, string> = {
  ready: 'bg-mint',
  resolved: 'bg-mint',
  analysing: 'bg-amber',
  filed: 'bg-amber',
  escalated: 'bg-amber',
  collecting: 'bg-rail-foreground/40',
}

function CaseList() {
  const navigate = useNavigate()
  const { caseId } = useParams()
  const { t } = useTranslation()
  const { data, error } = useCases()
  const cases = data ?? []

  function title(c: CaseSummary): string {
    return c.title || c.insurer || t('workspace.untitled')
  }

  function lastLine(c: CaseSummary): string {
    if (c.last_message) return c.last_message
    return [
      c.diagnosis,
      c.claim_amount != null && c.currency ? formatMoney(c.claim_amount, c.currency) : null,
    ]
      .filter(Boolean)
      .join(' — ')
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 pt-5">
        <span className="grid size-8 place-items-center rounded-lg bg-brand text-white">
          <ShieldCheckIcon className="size-5" aria-hidden />
        </span>
        <span className="font-display text-lg font-bold tracking-tight text-rail-foreground">Kavach</span>
      </div>

      <div className="px-4 pt-5">
        <button
          type="button"
          onClick={() => navigate('/app')}
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-rail-foreground/20 text-sm font-semibold text-rail-foreground transition-colors hover:bg-rail-foreground/10"
        >
          <PlusIcon className="size-4" aria-hidden />
          {t('workspace.newCase')}
        </button>
      </div>

      <p className="px-4 pt-6 text-xs font-medium text-rail-foreground/50">{t('workspace.yourCases')}</p>

      <nav className="mt-2 min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {error ? (
          <p className="px-2 text-xs text-rail-foreground/60">{t('workspace.loadError')}</p>
        ) : cases.length ? (
          <ul className="flex flex-col gap-0.5">
            {cases.map((c) => {
              const active = c.id === caseId
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/case/${c.id}`)}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'flex w-full flex-col gap-0.5 rounded-md border-l-2 px-3 py-2.5 text-left transition-colors',
                      active
                        ? 'border-brand bg-rail-foreground/10'
                        : 'border-transparent hover:bg-rail-foreground/5',
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <span className={cn('size-1.5 shrink-0 rounded-full', DOT[c.status] ?? 'bg-rail-foreground/30')} />
                      <span className="min-w-0 flex-1 truncate text-sm font-semibold text-rail-foreground">{title(c)}</span>
                      <span className="shrink-0 rounded border border-rail-foreground/20 px-1.5 py-px font-mono text-[10px] font-semibold text-rail-foreground/60">
                        {c.country}
                      </span>
                    </span>
                    <span className="flex items-center gap-2 pl-3.5 text-xs text-rail-foreground/50">
                      <span className="min-w-0 flex-1 truncate">{lastLine(c)}</span>
                      {c.last_message_at ? <span className="shrink-0">{timeAgo(c.last_message_at)}</span> : null}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="px-2 text-xs text-rail-foreground/50">{t('workspace.noCases')}</p>
        )}
      </nav>

      <div className="border-t border-rail-foreground/10 px-3 py-2">
        <AccountStrip />
      </div>
    </div>
  )
}

export function DocketRail() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Desktop spine */}
      <aside className="hidden w-72 shrink-0 border-r border-rail-foreground/10 bg-rail md:block">
        <CaseList />
      </aside>

      {/* Mobile: slim bar + sheet */}
      <header className="flex h-14 items-center gap-3 border-b border-line bg-surface px-4 md:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open cases"
          className="grid size-9 place-items-center rounded-md hover:bg-muted"
        >
          <MenuIcon className="size-5" aria-hidden />
        </button>
        <span className="font-display text-lg font-bold tracking-tight">Kavach</span>
      </header>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="w-72 bg-rail p-0">
          <SheetTitle className="sr-only">Your cases</SheetTitle>
          <CaseList />
        </SheetContent>
      </Sheet>
    </>
  )
}