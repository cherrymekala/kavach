import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AppHeader, Button, Countdown, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, FooterCTA, Input, Label, Stepper, Timeline } from '@/components'
import { useCase, useMarkFiled, useRecordReply } from '@/api/hooks'
import { formatDate } from '@/lib/dates'

const LADDERS: Record<string, string[]> = {
  IN: ['Insurer', 'Insurance Ombudsman', 'Consumer Court'],
  SG: ['Insurer', 'FIDReC', 'Courts'],
}

function todayISO(): string {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export function Tracker() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const markFiled = useMarkFiled(caseId ?? '')
  const recordReply = useRecordReply(caseId ?? '')
  const [replyOpen, setReplyOpen] = useState(false)
  const [outcome, setOutcome] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const ladder = LADDERS[kase?.country ?? 'IN'] ?? LADDERS.IN
  const steps = ladder.map((label, i) => ({
    label,
    detail: i === (kase?.escalation_step ?? 0) && kase?.next_deadline ? formatDate(kase.next_deadline) : undefined,
  }))

  const events = (kase?.events ?? []).map((e, i, arr) => ({
    label: e.text,
    detail: formatDate(e.at),
    hot: i === arr.length - 1,
  }))

  async function handleFiled() {
    setError(null)
    try {
      await markFiled.mutateAsync({ filed_on: todayISO(), step: kase?.escalation_step ?? 0 })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('tracker.errorFiled'))
    }
  }

  async function handleReply() {
    setError(null)
    try {
      await recordReply.mutateAsync({
        outcome,
        replied_on: todayISO(),
        amount_paid: amount ? Number(amount) : null,
      })
      setReplyOpen(false)
      setOutcome('')
      setAmount('')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('tracker.errorReply'))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <AppHeader title={t('tracker.title')} pack={kase?.country} />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-base font-bold">{t('tracker.step')}</h3>
              <Countdown deadline={kase?.next_deadline} />
            </div>
            <Stepper steps={steps} current={kase?.escalation_step ?? 0} />
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="font-display text-base font-bold">{t('tracker.actions')}</h3>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" loading={markFiled.isPending} onClick={handleFiled}>
                {t('tracker.markFiled')}
              </Button>
              <Button variant="outline" onClick={() => setReplyOpen(true)}>
                {t('tracker.recordReply')}
              </Button>
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </section>
        </div>

        <div className="flex flex-col gap-6">
          {events.length ? (
            <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
              <h3 className="font-display text-base font-bold">{t('tracker.history')}</h3>
              <Timeline items={events} />
            </section>
          ) : null}
        </div>
      </div>

      <FooterCTA
        primary={{ label: t('tracker.cta'), onClick: () => navigate(`/case/${caseId}/outcome`) }}
      />

      <Dialog open={replyOpen} onOpenChange={setReplyOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('tracker.recordReply')}</DialogTitle>
            <DialogDescription>{t('tracker.replySub')}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="tr-outcome">{t('tracker.outcome')}</Label>
              <Input id="tr-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="tr-amount">{t('tracker.amountPaid')}</Label>
              <Input
                id="tr-amount"
                type="number"
                inputMode="numeric"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplyOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleReply} loading={recordReply.isPending}>
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}