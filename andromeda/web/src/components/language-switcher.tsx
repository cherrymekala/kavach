import { useState } from 'react'
import { CheckIcon, LanguagesIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/cn'
import { SUPPORTED_LANGUAGES } from '@/i18n'

export interface LanguageSwitcherProps {
  /** Restrict the list (e.g. to a country pack's languages). Defaults to all supported languages. */
  languages?: { code: string; label: string }[]
}

/** Compact language dropdown — a globe icon that opens the language list. */
export function LanguageSwitcher({ languages = SUPPORTED_LANGUAGES }: LanguageSwitcherProps) {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const current = languages.find((l) => l.code === (i18n.resolvedLanguage ?? 'en')) ?? languages[0]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t('common.language')} title={t('common.language')}>
          <LanguagesIcon className="size-5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="end">
        <Command>
          <CommandList>
            <CommandGroup heading={t('common.language')}>
              {languages.map((l) => (
                <CommandItem
                  key={l.code}
                  value={l.label}
                  onSelect={() => {
                    i18n.changeLanguage(l.code)
                    setOpen(false)
                  }}
                >
                  <span className="flex-1 truncate">{l.label}</span>
                  <CheckIcon
                    className={cn('size-4 shrink-0', l.code === current?.code ? 'opacity-100' : 'opacity-0')}
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