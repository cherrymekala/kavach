import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BellIcon, BellOffIcon } from 'lucide-react'
import { Button } from '@/components'
import { disablePush, enablePush, pushState, type PushState } from '@/lib/push'

/** "Remind me on this phone": web push for "X days left" and insurer replies. */
export function RemindersCard() {
  const { t } = useTranslation()
  const [state, setState] = useState<PushState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    pushState().then(setState, () => setState('unsupported'))
  }, [])

  if (state === null || state === 'unsupported') return null

  async function toggle() {
    setBusy(true)
    setError(null)
    try {
      setState(state === 'on' ? await disablePush() : await enablePush())
    } catch (e) {
      console.error('[push]', e)
      setError(t('reminders.error'))
    } finally {
      setBusy(false)
    }
  }

  const on = state === 'on'
  return (
    <div className="flex flex-col gap-3 rounded-[22px] bg-card p-4 text-card-foreground sm:flex-row sm:items-center">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-brand">
        {on ? <BellIcon className="size-5" aria-hidden /> : <BellOffIcon className="size-5" aria-hidden />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold">{t(on ? 'reminders.onTitle' : 'reminders.title')}</p>
        <p className="text-sm text-muted-foreground">
          {state === 'blocked' ? t('reminders.blocked') : t(on ? 'reminders.onSub' : 'reminders.sub')}
        </p>
        {error ? <p className="mt-1 text-sm text-destructive">{error}</p> : null}
      </div>
      {state !== 'blocked' ? (
        <Button variant={on ? 'outline' : 'default'} loading={busy} onClick={toggle} className="self-start sm:self-center">
          {t(on ? 'reminders.turnOff' : 'reminders.turnOn')}
        </Button>
      ) : null}
    </div>
  )
}
