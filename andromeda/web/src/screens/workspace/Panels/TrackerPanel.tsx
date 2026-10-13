import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangleIcon,
  ArrowUpRightIcon,
  BellIcon,
  CheckCircle2Icon,
  FileTextIcon,
  MessageSquareReplyIcon,
  MicIcon,
  SendIcon,
  Trash2Icon,
  TrophyIcon,
  type LucideIcon,
} from 'lucide-react'
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Stepper,
} from '@/components'
import { useMarkFiled, usePack, useRecordReply } from '@/api/hooks'
import type { Case, CaseEvent } from '@/api/types'
import { daysUntil, formatDate } from '@/lib/dates'
import { cn } from '@/lib/cn'

function todayISO(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const EVENT_ICON: Record<string, LucideIcon> = {
  filed: SendIcon,
  reply: MessageSquareReplyIcon,
  escalated: ArrowUpRightIcon,
  reminder: BellIcon,
  warning: AlertTriangleIcon,
  resolved: TrophyIcon,
  rehearsal: MicIcon,
  documents_deleted: Trash2Icon,
}
const EVENT_TONE: Record<string, string> = {
  warning: 'bg-amber/15 text-amber',
  resolved: 'bg-mint/15 text-mint',
  escalated: 'bg-amber/15 text-amber',
}

const TRACKER_KINDS = new Set([
  'filed',
  'reply',
  'escalated',
  'reminder',
  'warning',
  'resolved',
  'rehearsal',
  'documents_deleted',
])

function History({ events }: { events: CaseEvent[] }) {
  const items = events
    .filter((e) => TRACKER_KINDS.has(e.kind))
    .sort((a, b) => String(b.at).localeCompare(String(a.at)))
  if (!items.length) return null
  return (
    <ol className="flex flex-col gap-4">
      {items.map((e, i) => {
        const Icon = EVENT_ICON[e.kind] ?? FileTextIcon
        return (
          <li key={`${e.at}-${i}`} className="flex gap-3">
            <span className={cn('grid size-8 shrink-0 place-items-center rounded-full', EVENT_TONE[e.kind] ?? 'bg-muted text-muted-foreground')}>
              <Icon className="size-4" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="text-sm">{e.text}</p>
              <p className="font-mono text-xs text-muted-foreground">{formatDate(e.at)}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

type Outcome = 'paid' | 'partly_paid' | 'rejected'

export function TrackerPanel({ caseId, kase }: { caseId: string; kase: Case }) {
  const { t } = useTranslation()
  const { data: pack } = usePack(kase?.country)
  const markFiled = useMarkFiled(caseId)
  const recordReply = useRecordReply(caseId)

  const [dialog, setDialog] = useState<'filed' | 'reply' | null>(null)
  const [date, setDate] = useState(todayISO())
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)

  const ladder = pack?.ladder ?? []
  const stepIndex = Math.min(kase.escalation_step ?? 0, Math.max(ladder.length - 1, 0))
  const step = ladder[stepIndex]
  const stepName = step?.step ?? ''
  const status = kase.status
  const days = daysUntil(kase.next_deadline)
  const lastStep = stepIndex === ladder.length - 1
  const warning = [...(kase.events ?? [])].reverse().find((e) => e.kind === 'warning')

  function open(kind: 'filed' | 'reply') {
    setError(null)
    setDate(todayISO())
    setOutcome(null)
    setAmount('')
    setDialog(kind)
  }

  async function save() {
    setError(null)
    try {
      if (dialog === 'filed') {
        await markFiled.mutateAsync({ filed_on: date, step: stepIndex })
      } else if (outcome) {
        await recordReply.mutateAsync({
          outcome,
          replied_on: date,
          amount_paid: outcome === 'rejected' || !amount ? null : Number(amount),
        })
      }
      setDialog(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('tracker.errorSave'))
    }
  }

  let now: { tone: string; title: string; body: string; actions: React.ReactNode }
  if (status === 'resolved') {
    now = {
      tone: 'border-mint/50 bg-mint/10',
      title: t('tracker.now.resolved.title'),
      body: t('tracker.now.resolved.body'),
      actions: null,
    }
  } else if (status === 'filed') {
    now = {
      tone: 'border-line bg-surface',
      title: t('tracker.now.waiting.title', { body: stepName }),
      body:
        days !== null && days < 0
          ? t('tracker.now.waiting.overdue')
          : t('tracker.now.waiting.body', { date: formatDate(kase.next_deadline) }),
      actions: <Button onClick={() => open('reply')}>{t('tracker.now.waiting.cta')}</Button>,
    }
  } else {
    const first = stepIndex === 0
    now = {
      tone: 'border-brand/40 bg-accent/40',
      title: first ? t('tracker.now.send.title') : t('tracker.now.next.title', { body: stepName }),
      body: first
        ? t('tracker.now.send.body', { body: step?.dispute_body ?? '', days: step?.deadline_days ?? '' })
        : t('tracker.now.next.body', { form: step?.form ?? '', body: step?.dispute_body ?? '' }),
      actions: <Button onClick={() => open('filed')}>{first ? t('tracker.now.send.cta') : t('tracker.now.next.cta')}</Button>,
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <header>
        <h2 className="font-display text-xl font-bold">{t('tracker.title')}</h2>
      </header>

      <div className={cn('flex flex-col gap-3 rounded-lg border p-5', now.tone)}>
        {status === 'filed' && days !== null && days >= 0 ? (
          <p className="font-display text-4xl font-extrabold tabular-nums">
            {days}
            <span className="ml-2 text-base font-semibold text-muted-foreground">{t('tracker.daysLeft', { count: days })}</span>
          </p>
        ) : null}
        <h3 className="font-display text-lg font-bold leading-tight">{now.title}</h3>
        <p className="text-sm text-muted-foreground">{now.body}</p>
        {now.actions ? <div className="flex flex-col gap-2 sm:flex-row">{now.actions}</div> : null}
        {status === 'escalated' && lastStep ? <p className="text-xs text-muted-foreground">{t('tracker.lastStep')}</p> : null}
      </div>

      {warning && status !== 'resolved' ? (
        <p className="flex gap-2 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm">
          <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-amber" aria-hidden />
          {warning.text}
        </p>
      ) : null}

      {ladder.length ? (
        <div className="flex flex-col gap-3">
          <h3 className="font-display text-base font-bold">{t('tracker.ladder')}</h3>
          <Stepper
            steps={ladder.map((s) => ({ label: s.step, detail: t('tracker.replyWithin', { days: s.deadline_days }) }))}
            current={status === 'resolved' ? ladder.length : stepIndex}
          />
        </div>
      ) : null}

      {kase.events?.length ? (
        <div className="flex flex-col gap-3">
          <h3 className="font-display text-base font-bold">{t('tracker.history')}</h3>
          <History events={kase.events} />
        </div>
      ) : null}

      <Dialog open={dialog !== null} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialog === 'filed' ? t('tracker.filedTitle', { body: stepName }) : t('tracker.replyTitle')}</DialogTitle>
            <DialogDescription>{dialog === 'filed' ? t('tracker.filedSub') : t('tracker.replySub')}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            {dialog === 'reply' ? (
              <div className="grid gap-2" role="radiogroup">
                {(['paid', 'partly_paid', 'rejected'] as const).map((o) => (
                  <button
                    key={o}
                    type="button"
                    role="radio"
                    aria-checked={outcome === o}
                    onClick={() => setOutcome(o)}
                    className={cn(
                      'flex items-center gap-3 rounded-xl border p-3 text-left text-sm font-semibold',
                      outcome === o ? 'border-brand bg-accent/50' : 'border-line',
                    )}
                  >
                    <CheckCircle2Icon className={cn('size-5', outcome === o ? 'text-brand' : 'text-muted')} aria-hidden />
                    {t(`tracker.outcomes.${o}`)}
                  </button>
                ))}
              </div>
            ) : null}
            {dialog === 'reply' && outcome && outcome !== 'rejected' ? (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="tr-amount">{t('tracker.amountPaid')}</Label>
                <Input id="tr-amount" type="number" inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} />
              </div>
            ) : null}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="tr-date">{dialog === 'filed' ? t('tracker.filedOn') : t('tracker.repliedOn')}</Label>
              <Input id="tr-date" type="date" max={todayISO()} value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={save} disabled={!date || (dialog === 'reply' && !outcome)} loading={markFiled.isPending || recordReply.isPending}>
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}