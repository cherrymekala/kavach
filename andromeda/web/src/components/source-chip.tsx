import { ArrowUpRightIcon } from 'lucide-react'

export interface SourceChipProps {
  label: string
  onClick?: () => void
}

/** Tappable citation — opens the source quote in a Sheet. */
export function SourceChip({ label, onClick }: SourceChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex max-w-full items-center gap-1 rounded font-mono text-xs font-bold text-brand hover:underline focus-visible:outline-2 focus-visible:outline-ring"
    >
      <span className="truncate">{label}</span>
      <ArrowUpRightIcon className="size-3 shrink-0" aria-hidden />
    </button>
  )
}