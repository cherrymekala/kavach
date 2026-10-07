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

/** Sticky bottom action bar — one primary action, optional ghost secondary. */
export function FooterCTA({ primary, secondary }: FooterCTAProps) {
  return (
    <div className="sticky bottom-0 flex gap-2 border-t border-border bg-background/95 px-4 py-3 backdrop-blur">
      {secondary ? (
        <Button variant="ghost" className="shrink-0 px-4" onClick={secondary.onClick}>
          {secondary.label}
        </Button>
      ) : null}
      <Button className="flex-1" loading={primary.loading} disabled={primary.disabled} onClick={primary.onClick}>
        {primary.label}
      </Button>
    </div>
  )
}