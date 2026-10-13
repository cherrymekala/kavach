import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { signOut } from 'firebase/auth'
import { LogOutIcon, MenuIcon, PlusIcon, ShieldCheckIcon } from 'lucide-react'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { auth } from '@/firebase'
import { useCases } from '@/api/hooks'
import type { CaseSummary, WithTitle } from '@/api/types'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/cn'

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
  const cases = (data ?? []) as (CaseSummary & WithTitle)[]

  function title(c: CaseSummary & WithTitle): string {
    return c.title || c.insurer || t('workspace.untitled')
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
                      <span className="truncate text-sm font-semibold text-rail-foreground">{title(c)}</span>
                    </span>
                    <span className="truncate pl-3.5 text-xs text-rail-foreground/50">
                      {[c.diagnosis, c.claim_amount != null && c.currency ? formatMoney(c.claim_amount, c.currency) : null]
                        .filter(Boolean)
                        .join(' — ') || c.country}
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

      <div className="flex items-center gap-1 border-t border-rail-foreground/10 px-3 py-3">
        <button
          type="button"
          onClick={() => void signOut(auth())}
          className="ml-auto flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-rail-foreground/70 hover:bg-rail-foreground/10 hover:text-rail-foreground"
        >
          <LogOutIcon className="size-4" aria-hidden />
          Sign out
        </button>
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