import { CheckIcon } from 'lucide-react'
import { cn } from '@/lib/cn'
import type { CountryCode, CountryOption } from './countries'

export interface CountryPickerProps {
  countries: CountryOption[]
  value: CountryCode
  onChange: (code: CountryCode) => void
}

export function CountryPicker({ countries, value, onChange }: CountryPickerProps) {
  return (
    <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Country">
      {countries.map((c) => {
        const selected = c.code === value
        return (
          <button
            key={c.code}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(c.code)}
            className={cn(
              'relative flex flex-col gap-1 rounded-xl border p-4 text-left transition-colors focus-visible:outline-2 focus-visible:outline-ring',
              selected ? 'border-brand bg-accent text-accent-foreground' : 'border-border hover:bg-muted',
            )}
          >
            {selected ? <CheckIcon className="absolute right-3 top-3 size-4 text-brand" aria-hidden /> : null}
            <span className="text-2xl leading-none">{c.flag}</span>
            <span className="mt-1 font-display font-bold">{c.name}</span>
            <span className="text-xs text-muted-foreground">
              {c.regulator} · {c.currency}
            </span>
          </button>
        )
      })}
    </div>
  )
}