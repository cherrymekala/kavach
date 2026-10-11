import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { GavelIcon, KeyboardIcon, MicIcon, MicOffIcon, SendIcon, SquareIcon } from 'lucide-react'
import { AppHeader, Button, FooterCTA, Input, LiveIndicator, Meter, Spinner } from '@/components'
import { useCase, usePack } from '@/api/hooks'
import { type Coaching, type Entry, useHearing } from '@/api/hearing'
import { cn } from '@/lib/cn'

// The Live model announces who is speaking ("Insurer's representative: ...").
const SPEAKER = /(Insurance Ombudsman|Ombudsman|FIDReC(?: mediator)?|Insurer['’]s representative)\s*:\s*/g

function splitSpeakers(text: string): { speaker: string | null; text: string }[] {
  const parts: { speaker: string | null; text: string }[] = []
  let speaker: string | null = null
  let last = 0
  for (const m of text.matchAll(SPEAKER)) {
    const before = text.slice(last, m.index).trim()
    if (before) parts.push({ speaker, text: before })
    speaker = m[1]
    last = (m.index ?? 0) + m[0].length
  }
  const rest = text.slice(last).trim()
  if (rest) parts.push({ speaker, text: rest })
  return parts
}

// Matches the server (agents/hearing.py): shorter replies are fillers and aren't scored.
const MIN_ANSWER_WORDS = 3

function tone(score: number): 'mint' | 'amber' | 'brand' {
  return score >= 4 ? 'mint' : score === 3 ? 'amber' : 'brand'
}

function CoachCard({ coach }: { coach: Coaching }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-mint/40 bg-mint/10 p-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="font-bold text-mint">{t('hearing.coach')}</span>
        <span className="font-mono text-xs font-semibold tabular-nums">{coach.score}/5</span>
      </div>
      <Meter value={coach.score / 5} tone={tone(coach.score)} />
      <p>{coach.feedback}</p>
      <details className="text-muted-foreground">
        <summary className="cursor-pointer font-semibold text-foreground">{t('hearing.tryThis')}</summary>
        <p className="mt-1 italic">“{coach.better_answer}”</p>
      </details>
    </div>
  )
}

function Turn({ entry }: { entry: Entry }) {
  const { t } = useTranslation()
  if (entry.kind === 'you') {
    return (
      <div className="flex flex-col items-end gap-2">
        <div className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
          {entry.text}
        </div>
        {entry.coach ? (
          <div className="w-full">
            <CoachCard coach={entry.coach} />
          </div>
        ) : entry.text.trim().split(/\s+/).length >= MIN_ANSWER_WORDS ? (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Spinner /> {t('hearing.scoring')}
          </span>
        ) : null}
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-2">
      {splitSpeakers(entry.text).map((part, i) => {
        const insurer = part.speaker?.startsWith('Insurer')
        return (
          <div key={i} className="max-w-[85%] self-start">
            {part.speaker ? (
              <span className={cn('mb-1 block text-xs font-bold', insurer ? 'text-amber' : 'text-brand')}>
                {part.speaker}
              </span>
            ) : null}
            <div
              className={cn(
                'rounded-lg rounded-bl-sm px-3 py-2 text-sm',
                insurer ? 'border border-amber/40 bg-amber/10' : 'bg-muted',
              )}
            >
              {part.text}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function Hearing() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase } = useCase(caseId)
  const { data: pack } = usePack(kase?.country)
  const hearing = useHearing(caseId)
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')
  const bottom = useRef<HTMLDivElement>(null)

  const body = pack?.ladder.at(-1)?.step ?? t('hearing.disputeBody')
  const ready = Boolean(kase?.assessment)

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [hearing.entries, hearing.yourTurn])

  if (hearing.state === 'done' && hearing.debrief) {
    const d = hearing.debrief
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-24">
        <AppHeader title={t('hearing.title')} />
        <section className="flex flex-col gap-3 rounded-2xl bg-primary p-6 text-primary-foreground">
          <span className="font-mono text-xs opacity-80">{t('hearing.debrief')}</span>
          {d.average_score !== null ? (
            <p className="font-display text-4xl font-extrabold tabular-nums">
              {d.average_score}
              <span className="text-lg opacity-70">/5</span>
            </p>
          ) : null}
          <p className="text-sm opacity-90">{d.summary}</p>
        </section>
        <section className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('hearing.tipsForReal')}</h3>
          {d.top_tips.map((tip, i) => (
            <div key={tip} className="flex items-start gap-3 rounded-xl border border-border bg-card p-4">
              <span className="font-display text-lg font-extrabold text-brand">{i + 1}</span>
              <p className="text-sm">{tip}</p>
            </div>
          ))}
        </section>
        <FooterCTA
          primary={{ label: t('hearing.cta'), onClick: () => navigate(`/case/${caseId}/tracker`) }}
          secondary={{ label: t('hearing.again'), onClick: hearing.start }}
        />
      </div>
    )
  }

  if (hearing.state === 'idle' || hearing.state === 'error') {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-24">
        <AppHeader title={t('hearing.title')} />
        <section className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-full bg-accent text-accent-foreground">
              <GavelIcon className="size-5" aria-hidden />
            </span>
            <div>
              <h3 className="font-display font-bold">{t('hearing.intro', { body })}</h3>
              <p className="text-sm text-muted-foreground">{t('hearing.introSub')}</p>
            </div>
          </div>
          <ul className="flex flex-col gap-2 text-sm">
            <li className="flex gap-2">
              <span className="font-bold text-brand">{body}</span>
              <span className="text-muted-foreground">{t('hearing.roleBody')}</span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-amber">{t('hearing.insurerRep')}</span>
              <span className="text-muted-foreground">{t('hearing.roleInsurer')}</span>
            </li>
          </ul>
          {hearing.error ? <p className="text-sm text-destructive">{hearing.error}</p> : null}
          {!ready ? <p className="text-sm text-muted-foreground">{t('hearing.needAnalysis')}</p> : null}
        </section>
        <section className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('hearing.tips')}</h3>
          {[t('hearing.tip1'), t('hearing.tip2'), t('hearing.tip3')].map((tip, i) => (
            <div key={tip} className="flex items-start gap-3 rounded-xl border border-border bg-card p-4">
              <span className="font-display text-lg font-extrabold text-brand">{i + 1}</span>
              <p className="text-sm">{tip}</p>
            </div>
          ))}
        </section>
        <FooterCTA
          primary={{ label: t('hearing.start'), onClick: hearing.start, disabled: !ready }}
          secondary={{ label: t('hearing.skip'), onClick: () => navigate(`/case/${caseId}/tracker`) }}
        />
      </div>
    )
  }

  const live = hearing.state === 'live'
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 pb-40">
      <AppHeader title={t('hearing.title')} />
      <div className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-2">
        <span className="text-sm font-semibold">{body}</span>
        {hearing.state === 'connecting' ? (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner /> {t('hearing.connecting')}
          </span>
        ) : hearing.state === 'ending' ? (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner /> {t('hearing.wrappingUp')}
          </span>
        ) : (
          <LiveIndicator label={t('hearing.live')} />
        )}
      </div>

      <div className="flex flex-col gap-4" aria-live="polite">
        {hearing.entries.map((e) => (
          <Turn key={e.id} entry={e} />
        ))}
        {hearing.yourTurn && live ? (
          <span className="self-center rounded-full bg-accent px-3 py-1 text-xs font-bold text-accent-foreground">
            {t('hearing.yourTurn')}
          </span>
        ) : null}
        <div ref={bottom} />
      </div>

      <div className="fixed inset-x-0 bottom-4 z-30 px-4">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 rounded-2xl border border-border bg-card p-2 shadow-lg">
          {typing ? (
            <form
              className="flex items-center gap-1"
              onSubmit={(e) => {
                e.preventDefault()
                hearing.sendText(draft)
                setDraft('')
              }}
            >
              <Input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={t('hearing.typePlaceholder')}
                disabled={!live}
                className="h-10 flex-1"
              />
              <Button type="submit" size="icon" disabled={!live || !draft.trim()} aria-label={t('hearing.send')}>
                <SendIcon className="size-5" />
              </Button>
            </form>
          ) : null}
          <div className="flex items-center justify-between gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTyping((v) => !v)}
              aria-label={t('hearing.typeInstead')}
              title={t('hearing.typeInstead')}
            >
              <KeyboardIcon className="size-5" />
            </Button>
            <Button
              size="lg"
              disabled={!live}
              onClick={hearing.toggleMic}
              className={cn('h-14 flex-1 rounded-full', hearing.micOn && 'bg-amber text-black hover:bg-amber/90')}
              aria-pressed={hearing.micOn}
            >
              {hearing.micOn ? <MicOffIcon className="size-5" /> : <MicIcon className="size-5" />}
              {hearing.micOn ? t('hearing.micOff') : t('hearing.micOn')}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              disabled={!live}
              onClick={hearing.end}
              aria-label={t('hearing.end')}
              title={t('hearing.end')}
            >
              <SquareIcon className="size-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
