import { MoonIcon, SunIcon } from 'lucide-react'
import { useTheme } from '@/lib/theme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Toggle colour theme"
      className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
    >
      {theme === 'dark' ? <SunIcon className="size-5" /> : <MoonIcon className="size-5" />}
    </button>
  )
}