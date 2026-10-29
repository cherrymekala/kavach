import { useTranslation } from 'react-i18next'
import { Spinner } from '@/components'

/**
 * Shown between Stripe redirecting back and its webhook unlocking the case.
 *
 * Without this the patient lands on a screen that still says "Unlock your appeal pack" seconds
 * after paying, which reads like the payment failed.
 */
export function ConfirmingPayment() {
  const { t } = useTranslation()
  return (
    <section
      aria-live="polite"
      className="flex items-start gap-3 rounded-2xl border border-brand/30 bg-accent/40 p-5"
    >
      <Spinner className="mt-0.5 size-5 shrink-0" />
      <div className="min-w-0">
        <h2 className="font-display text-lg font-bold">{t('unlock.confirmingTitle')}</h2>
        <p className="text-sm text-muted-foreground">{t('unlock.confirmingSub')}</p>
      </div>
    </section>
  )
}
