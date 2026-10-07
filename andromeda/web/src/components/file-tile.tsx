import { XIcon } from 'lucide-react'
import { Pill } from '@/components/ui/pill'
import { SourceKindIcon } from './source-kind-icon'

const DOC_TYPE_LABELS: Record<string, string> = {
  policy: 'Policy document',
  rejection_letter: 'Rejection letter',
  discharge_summary: 'Discharge summary',
  bill: 'Hospital bill',
  other: 'Document',
}

export interface FileTileProps {
  filename: string
  docType?: string
  pages?: number | null
  warning?: string | null
  onRemove?: () => void
}

export function FileTile({ filename, docType, pages, warning, onRemove }: FileTileProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border p-3">
      <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
        <SourceKindIcon kind={docType ?? 'other'} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{filename}</p>
        <p className="truncate text-xs text-muted-foreground">
          {DOC_TYPE_LABELS[docType ?? ''] ?? 'Unlabelled'}
          {pages ? ` · ${pages} pages` : ''}
        </p>
      </div>
      {warning ? <Pill tone="warn">Check</Pill> : <Pill tone="ok">Read</Pill>}
      {onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${filename}`}
          className="grid size-8 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <XIcon className="size-4" />
        </button>
      ) : null}
    </div>
  )
}