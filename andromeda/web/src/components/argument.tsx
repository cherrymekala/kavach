import { SourceChip } from './source-chip'

export interface ArgumentSource {
  ref: string
  quote?: string
  kind?: string
}

export interface ArgumentProps {
  claim: string
  explanation: string
  sources: ArgumentSource[]
  onSource?: (source: ArgumentSource) => void
}

/** One sourced argument — the product's trust block. */
export function Argument({ claim, explanation, sources, onSource }: ArgumentProps) {
  return (
    <div className="flex flex-col gap-1 border-l-[3px] border-mint py-1 pl-3">
      <p className="font-bold">{claim}</p>
      <p className="text-sm text-muted-foreground">{explanation}</p>
      {sources.length ? (
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {sources.map((s) => (
            <SourceChip key={s.ref} label={s.ref} onClick={() => onSource?.(s)} />
          ))}
        </div>
      ) : null}
    </div>
  )
}