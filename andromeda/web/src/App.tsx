import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'

export function App() {
  return (
    <TooltipProvider>
      <div className="min-h-dvh bg-background text-foreground">
        <main className="mx-auto w-full max-w-md px-4 py-6">
          <Suspense
            fallback={<div className="py-16 text-center text-sm text-muted-foreground">Loading…</div>}
          >
            <Outlet />
          </Suspense>
        </main>
        <Toaster position="top-center" />
      </div>
    </TooltipProvider>
  )
}