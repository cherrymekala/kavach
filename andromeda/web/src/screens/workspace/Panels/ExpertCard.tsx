import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2Icon, UserRoundSearchIcon } from 'lucide-react'
import {
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Textarea,
} from '@/components'
import { useExpertOffer, useRequestExpert } from '@/api/hooks'
import type { Case } from '@/api/types'
import { formatDate } from '@/lib/dates'
import { cn } from '@/lib/cn'

// What the triage team sees (agents/expert.py SHARED), shown before the patient consents.
const SHARED = ['country', 'insurer', 'reason', 'amounts', 'assessment', 'deadline', 'contact', 'note'] as const

/**
 * Handoff to a human advocate: suggested for weak or high-value cases, available on any.
 * The patient sees exactly what is shared (a summary, never documents) and consents first.
 */
export function ExpertCard({ kase }: { kase: Case }) {
  const { t } = useTranslation()
  const { data: offer } = useExpertOffer(kase.id)
  const request = useRequestExpert(kase.id)
  const [open, setOpen] = useState(false)
  const [phone, setPhone] = useState(kase.complainant?.mobile ?? '')
  const [email, setEmail] = useState(kase.complainant?.email ?? '')
  const [note, setNote] = useState('')
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!offer) return null

  if (offer.requested_at) {
    return (
      <p className="flex items-start gap-2 rounded-[22px] bg-card p-4 text-sm">
        <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-mint" aria-hidden />
        {t('expert.requested', { date: formatDate(offer.requested_at) })}
      </p>
    )
  }

  async function submit() {
    setError(null)
    try {
      await request.mutateAsync({ consent, phone: phone || null, email: email || null, note })
      setOpen(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('expert.error'))
    }
  }

  const suggested = Boolean(offer.reason)

  return (
    <>
      {suggested ? (
        <section className="flex flex-col gap-3 rounded-[24px] bg-card p-5 shadow-[0_18px_40px_rgb(46_31_184/0.08)]">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground">
              <UserRoundSearchIcon className="size-5" aria-hidden />
            </span>
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="text-base font-extrabold tracking-tight">{t('expert.title')}</h3>
              <p className="text-sm text-muted-foreground">{t(`expert.why.${offer.reason}`)}</p>
            </div>
          </div>
          <Button className="self-start" onClick={() => setOpen(true)}>
            {t('expert.cta')}
          </Button>
        </section>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className="self-start text-sm font-semibold text-brand hover:underline">
          {t('expert.link')}
        </button>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('expert.title')}</DialogTitle>
            <DialogDescription>{t('expert.how')}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="rounded-2xl bg-muted/60 p-4 text-sm">
              <p className="font-semibold">{t('expert.sharedTitle')}</p>
              <ul className="mt-2 list-disc pl-5 text-muted-foreground">
                {SHARED.map((k) => (
                  <li key={k}>{t(`expert.shared.${k}`)}</li>
                ))}
              </ul>
              <p className="mt-2 font-semibold">{t('expert.notShared')}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="expert-phone">{t('filing.mobile')}</Label>
                <Input id="expert-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="expert-email">{t('filing.email')}</Label>
                <Input id="expert-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expert-note">{t('expert.note')}</Label>
              <Textarea id="expert-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder={t('expert.notePlaceholder')} />
            </div>
            <label className={cn('flex items-start gap-3 rounded-2xl border p-3 text-sm', consent ? 'border-brand' : 'border-border')}>
              <Checkbox checked={consent} onCheckedChange={(v) => setConsent(v === true)} className="mt-0.5" />
              <span>{t('expert.consent')}</span>
            </label>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </div>
          <DialogFooter>
            <Button onClick={submit} loading={request.isPending} disabled={!consent || (!phone.trim() && !email.trim())}>
              {t('expert.send')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
