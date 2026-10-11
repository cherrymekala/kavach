import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components'
import { SourceKindIcon, type ArgumentSource } from '@/components'
import { Badge } from '@/components/ui/badge'

export interface SourceSheetProps {
  source: ArgumentSource | null
  onClose: () => void
}

/** Bottom sheet showing the full text of a tapped citation. */
export function SourceSheet({ source, onClose }: SourceSheetProps) {
  return (
    <Sheet open={source !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="bottom" className="max-w-2xl mx-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <SourceKindIcon kind={source?.kind ?? 'regulation'} className="size-5 text-brand" />
            <span className="min-w-0 truncate">{source?.ref}</span>
          </SheetTitle>
          <SheetDescription>
            <Badge variant="secondary">Source</Badge>
          </SheetDescription>
        </SheetHeader>
        {source?.quote ? (
          <p className="px-4 pb-6 text-sm leading-relaxed text-foreground">{source.quote}</p>
        ) : (
          <p className="px-4 pb-6 text-sm text-muted-foreground">No excerpt available.</p>
        )}
      </SheetContent>
    </Sheet>
  )
}