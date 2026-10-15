import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LayoutListIcon, type LucideIcon } from 'lucide-react'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components'
import { cn } from '@/lib/cn'

export interface Section {
  id: string
  label: string
  icon: LucideIcon
  /** Optional small hint shown at the right of a nav item. */
  badge?: string
}

interface SectionNavProps {
  sections: Section[]
  active: string
  onSelect: (id: string) => void
}

/** Presentational list of section buttons — used in the desktop rail and the mobile sheet. */
export function SectionList({ sections, active, onSelect }: SectionNavProps) {
  return (
    <div className="flex flex-col gap-1">
      {sections.map((s) => {
        const isActive = s.id === active
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition-colors',
              isActive
                ? 'bg-brand-soft text-brand'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            <s.icon className="size-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1 truncate">{s.label}</span>
            {s.badge ? <span className="shrink-0 text-[11px] font-medium text-muted-foreground">{s.badge}</span> : null}
          </button>
        )
      })}
    </div>
  )
}

interface SectionDockProps extends SectionNavProps {
  /** Lift the button up (when the chat panel is open beneath it). */
  lifted?: boolean
}

/** Mobile-only: a floating button (above the message button) that opens a bottom sheet of sections. */
export function SectionDock({ sections, active, onSelect, lifted = false }: SectionDockProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  return (
    <div className="lg:hidden">
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t('workspace.sections')}
        className={cn(
          'absolute right-4 z-40 grid size-12 place-items-center rounded-full border border-line bg-surface text-foreground shadow-float transition-all duration-200 hover:scale-105',
          lifted ? 'bottom-[9.75rem]' : 'bottom-[4.75rem]',
        )}
      >
        <LayoutListIcon className="size-5" aria-hidden />
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="max-h-[70vh] overflow-y-auto p-0">
          <SheetTitle className="sr-only">{t('workspace.sections')}</SheetTitle>
          <SheetDescription className="sr-only">{t('workspace.sectionsHint')}</SheetDescription>
          <div className="px-4 pt-3 pb-4">
            <p className="px-3 pb-2 font-display text-sm font-bold text-muted-foreground">{t('workspace.sections')}</p>
            <SectionList
              sections={sections}
              active={active}
              onSelect={(id) => {
                onSelect(id)
                setOpen(false)
              }}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}