import { Button } from '@/components/ui/button'

export interface FooterCTAProps {
  primary: {
    label: string
    onClick?: () => void
    loading?: boolean
    disabled?: boolean
  }
  secondary?: {
    label: string
    onClick?: () => void
  }
}

/**
 * Bottom action bar. Pinned to the bottom on phones; a normal in-flow button
 * bar on tablet/desktop (so it doesn't float mid-page on large screens).
 */
export function FooterCTA({ primary, secondary }: FooterCTAProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 backdrop-blur md:static md:border-0 md:bg-transparent md:backdrop-blur-none">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-end gap-2 px-4 py-3 sm:px-6 md:px-0 md:py-0">
        {secondary ? (
          <Button variant="outline" className="shrink-0" onClick={secondary.onClick}>
            {secondary.label}
          </Button>
        ) : null}
        <Button
          size="lg"
          className="flex-1 md:flex-none"
          loading={primary.loading}
          disabled={primary.disabled}
          onClick={primary.onClick}
        >
          {primary.label}
        </Button>
      </div>
    </div>
  )
}