import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'

export function App() {
  return (
    <TooltipProvider>
      <div className="min-h-dvh bg-background text-foreground">
        <Suspense fallback={<div className="py-16 text-center text-sm text-muted-foreground">Loading…</div>}>
          <Outlet />
        </Suspense>
        <Toaster position="top-center" />
      </div>
    </TooltipProvider>
  )
}