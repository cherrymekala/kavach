import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckIcon, CopyIcon, HospitalIcon, ScaleIcon, StethoscopeIcon, UserIcon, type LucideIcon } from 'lucide-react'
import { Button, ShieldHero, SourceKindIcon, type ArgumentSource } from '@/components'
import { SourceSheet } from '@/screens/chances/SourceSheet'
import type { PreauthCheck } from '@/api/types'

// Who has to act is a label with an icon, never colour alone.
const WHO: Record<string, LucideIcon> = { hospital: HospitalIcon, doctor: StethoscopeIcon, you: UserIcon }

/** A draft the patient hands on (doctor's note, reconsideration request), with a copy button. */
function Draft({ title, sub, text }: { title: string; sub: string; text: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  if (!text) return null
  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }
  return (
    <section className="flex flex-col gap-3 rounded-[24px] bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-extrabold tracking-tight">{title}</h3>
          <p className="text-sm text-muted-foreground">{sub}</p>
        </div>
        <Button size="sm" variant="outline" onClick={copy} aria-label={t('letter.copy')}>
          {copied ? <CheckIcon className="text-mint" aria-hidden /> : <CopyIcon aria-hidden />}
          {copied ? t('letter.copied') : t('letter.copy')}
        </Button>
      </div>
      <p className="rounded-2xl bg-muted/60 p-4 text-sm leading-relaxed whitespace-pre-line">{text}</p>
    </section>
  )
}

/**
 * Cashless refused while the patient is in hospital (agents/preauth.py): what happened, who
 * does what in the next hours, the time limits that apply, and the two drafts to hand on.
 */
export function PreauthPanel({ check }: { check: PreauthCheck }) {
  const { t } = useTranslation()
  const [source, setSource] = useState<ArgumentSource | null>(null)
  const actions = check.actions ?? []
  const rules = check.rules ?? []

  return (
    <section className="flex flex-col gap-8">
      <ShieldHero tone="mixed" eyebrow={t('preauth.title')} footer={check.summary}>
        {t(`preauth.status.${check.status}`, { defaultValue: check.status })}
      </ShieldHero>

      {actions.length ? (
        <div className="flex flex-col gap-3">
          <h2 className="text-xl font-extrabold tracking-tight">{t('preauth.doNow')}</h2>
          <ol className="flex flex-col gap-2">
            {actions.map((a, i) => {
              const Icon = WHO[a.who] ?? UserIcon
              return (
                <li key={`${i}-${a.step}`} className="flex gap-3 rounded-[22px] bg-card p-4">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent text-sm font-extrabold text-accent-foreground">
                    {i + 1}
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <span className="flex w-fit items-center gap-1.5 rounded-full bg-muted px-2.5 py-0.5 text-xs font-bold">
                      <Icon className="size-3.5" aria-hidden />
                      {t(`preauth.who.${a.who}`, { defaultValue: a.who })}
                    </span>
                    <p className="text-[15px] leading-snug font-semibold">{a.step}</p>
                    {a.why ? <p className="text-sm text-muted-foreground">{a.why}</p> : null}
                    {(a.sources ?? []).map((s, j) => (
                      <button
                        key={`${s.ref}-${j}`}
                        type="button"
                        onClick={() => setSource({ ref: s.ref, quote: s.quote, kind: s.kind })}
                        className="flex w-fit items-center gap-1.5 text-xs font-semibold text-brand hover:underline"
                      >
                        <SourceKindIcon kind={s.kind} className="size-3.5" />
                        {s.ref}
                      </button>
                    ))}
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      ) : null}

      {rules.length ? (
        <div className="flex flex-col gap-3">
          <h2 className="text-xl font-extrabold tracking-tight">{t('preauth.rules')}</h2>
          {rules.map((r, i) => (
            <figure key={`${r.ref}-${i}`} className="flex gap-3 rounded-[22px] bg-accent p-4 text-accent-foreground">
              <ScaleIcon className="mt-0.5 size-4 shrink-0" aria-hidden />
              <div className="flex min-w-0 flex-col gap-1">
                <blockquote className="text-sm leading-relaxed text-foreground">“{r.quote}”</blockquote>
                <figcaption className="text-xs font-semibold">{r.ref}</figcaption>
              </div>
            </figure>
          ))}
        </div>
      ) : null}

      <Draft title={t('preauth.doctorNote')} sub={t('preauth.doctorNoteSub')} text={check.doctor_note ?? ''} />
      <Draft title={t('preauth.request')} sub={t('preauth.requestSub')} text={check.request ?? ''} />

      {check.fallback ? (
        <div className="flex flex-col gap-2 rounded-[24px] border border-border p-5">
          <h3 className="text-base font-extrabold tracking-tight">{t('preauth.fallback')}</h3>
          <p className="text-sm leading-relaxed">{check.fallback}</p>
        </div>
      ) : null}

      <p className="text-xs leading-relaxed text-muted-foreground">{check.disclaimer}</p>
      <SourceSheet source={source} onClose={() => setSource(null)} />
    </section>
  )
}
