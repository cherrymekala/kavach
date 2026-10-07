import { useState } from 'react'
import { CheckIcon, ChevronsUpDownIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/cn'
import { ALL_DIALS } from '@/lib/dials'

export interface CountrySelectProps {
  /** Dial code, e.g. `+91`. */
  value: string
  onChange: (dial: string) => void
}

export function CountrySelect({ value, onChange }: CountrySelectProps) {
  const [open, setOpen] = useState(false)
  const selected = ALL_DIALS.find((d) => d.dial === value) ?? ALL_DIALS[0]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="Country dial code"
          className="w-[128px] justify-between"
        >
          <span className="truncate">
            {selected.flag} {selected.dial}
          </span>
          <ChevronsUpDownIcon className="size-4 opacity-50" aria-hidden />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search country…" />
          <CommandList>
            <CommandEmpty>No country found.</CommandEmpty>
            <CommandGroup>
              {ALL_DIALS.map((d) => (
                <CommandItem
                  key={d.code}
                  value={d.label}
                  onSelect={() => {
                    onChange(d.dial)
                    setOpen(false)
                  }}
                >
                  <span className="truncate">{d.label}</span>
                  <CheckIcon
                    className={cn('ml-auto size-4 shrink-0', value === d.dial ? 'opacity-100' : 'opacity-0')}
                    aria-hidden
                  />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}