import { cn } from '@/lib/cn'

export interface LanguagePickerProps {
  languages: { code: string; label: string }[]
  value: string
  onChange: (code: string) => void
}

export function LanguagePicker({ languages, value, onChange }: LanguagePickerProps) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {languages.map((l) => (
        <button
          key={l.code}
          type="button"
          onClick={() => onChange(l.code)}
          aria-pressed={l.code === value}
          className={cn(
            'rounded-lg border px-3 py-2.5 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ring',
            l.code === value
              ? 'border-brand bg-accent text-accent-foreground'
              : 'border-border text-foreground hover:bg-muted',
          )}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}