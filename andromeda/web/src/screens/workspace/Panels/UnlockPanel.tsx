import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { CheckIcon, LockIcon } from 'lucide-react'
import { Button } from '@/components'
import { caseKey } from '@/api/hooks'
import { payForPack } from '@/api/payments'
import type { PackInfo } from '@/api/types'
import { useAuth } from '@/auth'
import { formatMoney } from '@/lib/money'

/** Shown when payments are on and this case's appeal pack isn't unlocked yet. */
export function UnlockPanel({ caseId, price }: { caseId: string; price: PackInfo }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const amount = formatMoney((price.price_amount ?? 0) / 100, price.price_currency ?? 'INR')

  async function unlock() {
    setError(null)
    setBusy(true)
    try {
      const paid = await payForPack(caseId, user?.phoneNumber)
      if (paid) queryClient.setQueryData(caseKey(caseId), paid)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('unlock.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-brand/30 bg-accent/40 p-5">
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
          <LockIcon className="size-4" aria-hidden />
        </span>
        <div>
          <h2 className="font-display text-lg font-bold">{t('unlock.title')}</h2>
          <p className="text-sm text-muted-foreground">{t('unlock.sub')}</p>
        </div>
      </div>
      <ul className="flex flex-col gap-1.5 text-sm">
        {(['letter', 'form', 'rehearsal'] as const).map((k) => (
          <li key={k} className="flex items-center gap-2">
            <CheckIcon className="size-4 shrink-0 text-mint" aria-hidden />
            {t(`unlock.items.${k}`)}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={unlock} loading={busy}>
          {t('unlock.cta', { amount })}
        </Button>
        <span className="text-xs text-muted-foreground">{t('unlock.note')}</span>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </section>
  )
}
