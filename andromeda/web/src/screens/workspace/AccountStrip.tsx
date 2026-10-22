import { signOut } from 'firebase/auth'
import { useTranslation } from 'react-i18next'
import { ChevronUpIcon, LogOutIcon, MessageCircleIcon, UserRoundIcon } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components'
import { auth } from '@/firebase'
import { useAuth } from '@/auth'

/** Digits only, so a number pasted as "+1 (555) 123-4567" still builds a valid wa.me link. */
const WHATSAPP = (import.meta.env.VITE_WHATSAPP_NUMBER ?? '').replace(/\D/g, '')
// The user sends this, so it stays in English: the bot answers in English today.
const WHATSAPP_PREFILL = 'Hi Kavach, I need help with a health insurance claim.'

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
        {/* The same WhatsApp channel the backend serves; hidden until VITE_WHATSAPP_NUMBER
            is set, so we never ship a dead link. Reuses the translated start.* copy. */}
        {WHATSAPP && (
          <a
            href={`https://wa.me/${WHATSAPP}?text=${encodeURIComponent(WHATSAPP_PREFILL)}`}
            target="_blank"
            rel="noreferrer"
            className="flex w-full items-start gap-2 rounded-md px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            <MessageCircleIcon className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1">
              {t('start.whatsapp')}
              <span className="block text-xs font-normal text-muted-foreground">
                {t('start.whatsappDesc')}
              </span>
            </span>
          </a>
        )}
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