import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { ShieldCheckIcon } from 'lucide-react'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { LanguageSwitcher, ThemeToggle } from '@/components'

export function App() {
  return (
    <TooltipProvider>
      <div className="flex h-dvh flex-col overflow-hidden bg-background text-foreground">
        <header className="z-20 shrink-0 border-b border-border bg-background/85 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-5xl items-center gap-3 px-4 sm:px-6">
            <div className="flex items-center gap-2.5">
              <span className="grid size-8 place-items-center rounded-lg bg-brand text-primary-foreground">
                <ShieldCheckIcon className="size-5" aria-hidden />
              </span>
              <span className="font-display text-lg font-bold tracking-tight">Kavach</span>
            </div>
            <div className="ml-auto flex items-center gap-1">
              <LanguageSwitcher />
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-5xl px-4 pt-6 pb-28 sm:px-6 md:pb-12">
            <Suspense
              fallback={<div className="py-16 text-center text-sm text-muted-foreground">Loading…</div>}
            >
              <Outlet />
            </Suspense>
          </div>
        </main>

        <Toaster position="top-center" />
      </div>
    </TooltipProvider>
  )
}