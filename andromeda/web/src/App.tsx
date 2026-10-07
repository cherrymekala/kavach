import { Outlet } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useTheme } from './lib/theme'

export function App() {
  const { theme, toggle } = useTheme()

  return (
    <TooltipProvider>
      <div className="min-h-dvh bg-background text-foreground">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="font-display text-lg font-extrabold tracking-tight">Kavach</span>
          <button
            type="button"
            onClick={toggle}
            className="rounded-md bg-secondary px-3 py-1.5 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
          >
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
        </header>
        <main className="mx-auto w-full max-w-md px-4 py-6">
          <Outlet />
        </main>
        <Toaster position="top-center" />
      </div>
    </TooltipProvider>
  )
}