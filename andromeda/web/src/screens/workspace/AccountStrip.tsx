import { signOut } from 'firebase/auth'
import { useTranslation } from 'react-i18next'
import { ChevronUpIcon, LogOutIcon, UserRoundIcon } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components'
import { auth } from '@/firebase'
import { useAuth } from '@/auth'

/** The account strip at the foot of the docket rail: avatar + number, tap to sign out. */
export function AccountStrip() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const phone = user?.phoneNumber

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-rail-foreground/10 focus-visible:outline-2 focus-visible:outline-rail-foreground/40"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand text-white">
            <UserRoundIcon className="size-5" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-rail-foreground">
              {phone ?? t('account.placeholder')}
            </span>
            <span className="block text-xs text-rail-foreground/50">{t('account.signedInAs')}</span>
          </span>
          <ChevronUpIcon className="size-4 shrink-0 text-rail-foreground/50" aria-hidden />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" side="top" sideOffset={8} className="w-56 p-1.5">
        <button
          type="button"
          onClick={() => void signOut(auth())}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          <LogOutIcon className="size-4" aria-hidden />
          {t('account.signOut')}
        </button>
      </PopoverContent>
    </Popover>
  )
}