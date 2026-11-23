import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRightIcon, CalendarClockIcon, ClipboardPasteIcon, ShieldCheckIcon, UploadIcon } from 'lucide-react'
import { Button, KavachMark, KavachPlates, ShieldHero, Textarea } from '@/components'
import { previewLetter, type PreviewResult } from '@/api/preview'
import { useAuth } from '@/auth'
import { keepLetter } from '@/lib/pendingLetter'
import { formatMoney } from '@/lib/money'
import { daysUntil, formatDate } from '@/lib/dates'
import { cn } from '@/lib/cn'

const COUNTRIES = [
  { code: 'IN', key: 'india' },
  { code: 'SG', key: 'singapore' },
  { code: 'MY', key: 'malaysia' },
] as const

/**
 * Try before signing in: a visitor (often from a /guides page) checks their rejection letter
 * and sees the decoded reason, how similar Ombudsman cases ended and their deadline. Only then
 * do we ask for a phone number, to build the appeal from the same letter.
 */
export function Check() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [country, setCountry] = useState<string>(i18n.language === 'ms' ? 'MY' : i18n.language === 'zh' ? 'SG' : 'IN')
  const [pasting, setPasting] = useState(false)
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PreviewResult | null>(null)

  async function check(f: File) {
    setFile(f)
    setBusy(true)
    setError(null)
    try {
      setResult(await previewLetter(f, country))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('check.error'))
    } finally {
      setBusy(false)
    }
  }

  function buildAppeal() {
    if (file) keepLetter({ file, country })
    if (user) navigate('/check/continue')
    else navigate('/', { state: { from: '/check/continue' } })
  }

  function reset() {
    setResult(null)
    setFile(null)
    setText('')
    setError(null)
  }

  const header = (
    <header className="flex items-center justify-between gap-3 py-4">
      <a href="/guides" className="flex items-center gap-2 font-display text-xl font-extrabold tracking-[-0.04em]">
        <KavachMark animate={false} className="h-7 text-brand" />
        kavach
      </a>
      <Link to={user ? '/app' : '/'} className="text-sm font-bold text-brand underline">
        {user ? t('check.myCases') : t('check.signIn')}
      </Link>
    </header>
  )

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-xl flex-col gap-6 px-4 pb-16">
        {header}
        {busy ? (
          <div className="flex flex-col items-center gap-5 py-16 text-center" aria-live="polite">
            <KavachPlates size={160} formed={1} />
            <p className="font-display text-xl font-bold tracking-[-0.03em]">{t('check.reading')}</p>
            <p className="max-w-[36ch] text-sm text-muted-foreground">{t('check.readingSub')}</p>
          </div>
        ) : result ? (
          <Result result={result} onBuild={buildAppeal} onReset={reset} />
        ) : (
          <>
            <div className="flex flex-col gap-3 pt-4">
              <h1 className="font-display text-[2rem] leading-[1.1] font-bold tracking-[-0.035em] text-balance">{t('check.title')}</h1>
              <p className="text-muted-foreground">{t('check.sub')}</p>
            </div>

            <div className="flex w-fit gap-1 rounded-full border border-line bg-surface p-1" role="radiogroup" aria-label={t('check.country')}>
              {COUNTRIES.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  role="radio"
                  aria-checked={country === c.code}
                  onClick={() => setCountry(c.code)}
                  className={cn('rounded-full px-4 py-2 text-sm font-semibold', country === c.code ? 'bg-primary text-primary-foreground' : 'text-muted-foreground')}
                >
                  {t(`check.countries.${c.key}`)}
                </button>
              ))}
            </div>

            {pasting ? (
              <div className="flex flex-col gap-3">
                <Textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} placeholder={t('check.pastePlaceholder')} maxLength={12000} />
                <Button
                  className="h-12"
                  disabled={text.trim().length < 40}
                  onClick={() => check(new File([text.trim()], 'rejection-letter.txt', { type: 'text/plain' }))}
                >
                  {t('check.explain')}
                </Button>
              </div>
            ) : (
              <label className="flex cursor-pointer flex-col items-center gap-3 rounded-[24px] border-2 border-dashed border-line bg-surface px-6 py-10 text-center transition-colors hover:border-brand">
                <span className="grid size-14 place-items-center rounded-full bg-accent text-brand">
                  <UploadIcon className="size-6" aria-hidden />
                </span>
                <span className="font-bold">{t('check.upload')}</span>
                <span className="text-sm text-muted-foreground">{t('check.uploadHint')}</span>
                <input
                  type="file"
                  accept="image/*,application/pdf,.txt"
                  className="sr-only"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    e.target.value = ''
                    if (f) check(f)
                  }}
                />
              </label>
            )}
            <button type="button" className="flex items-center gap-2 self-start text-sm font-semibold text-brand" onClick={() => setPasting((v) => !v)}>
              {pasting ? <UploadIcon className="size-4" aria-hidden /> : <ClipboardPasteIcon className="size-4" aria-hidden />}
              {pasting ? t('check.uploadInstead') : t('check.pasteInstead')}
            </button>

            {error ? <p className="rounded-2xl bg-destructive/10 p-4 text-sm text-destructive">{error}</p> : null}

            <p className="flex gap-2 text-xs text-muted-foreground">
              <ShieldCheckIcon className="size-4 shrink-0 text-mint" aria-hidden />
              {t('check.privacy')}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

function Result({ result, onBuild, onReset }: { result: PreviewResult; onBuild: () => void; onReset: () => void }) {
  const { t } = useTranslation()
  if (!result.is_rejection) {
    return (
      <div className="flex flex-col gap-4 pt-6">
        <h1 className="font-display text-2xl font-bold tracking-[-0.03em]">{t('check.notLetterTitle')}</h1>
        <p className="text-muted-foreground">{t('check.notLetterSub')}</p>
        <Button className="h-12 self-start" onClick={onReset}>{t('check.tryAgain')}</Button>
      </div>
    )
  }
  const cat = result.rejection_category ?? 'other'
  const money = result.claim_amount && result.currency ? formatMoney(result.claim_amount, result.currency) : null
  const left = daysUntil(result.deadline)
  const g = result.guide
  const insurer = prettyName(result.insurer) ?? t('check.yourInsurer')
  return (
    <div className="flex flex-col gap-4 pt-2">
      <ShieldHero
        tone="mixed"
        eyebrow={t(`summary.category.${cat}`, { defaultValue: t('check.rejected') })}
        footer={t(`summary.meaning.${cat}`, { defaultValue: '' })}
      >
        {money
          ? t('check.headline', { insurer, amount: money })
          : t('check.headlineNoAmount', { insurer })}
      </ShieldHero>

      {result.rejection_reason ? (
        <div className="rounded-[22px] bg-card p-5">
          <h2 className="text-sm font-bold">{t('check.theirWords')}</h2>
          <p className="mt-3 rounded-2xl bg-muted/60 p-4 text-[15px] leading-relaxed">“{result.rejection_reason}”</p>
          {result.cited_clause ? <p className="mt-2 text-xs text-muted-foreground">{result.cited_clause}</p> : null}
        </div>
      ) : null}

      {g ? (
        <a href={`/guides/${g.slug}`} className="flex items-center gap-4 rounded-[22px] bg-primary p-5 text-primary-foreground">
          <span className="font-display text-4xl font-bold tracking-[-0.04em]">{g.won_pct}%</span>
          <span className="min-w-0 flex-1 text-sm leading-snug">
            {t('check.odds', { total: g.total.toLocaleString() })}
            <span className="mt-1 flex items-center gap-1 font-bold underline">{t('check.readGuide')} <ArrowRightIcon className="size-4" aria-hidden /></span>
          </span>
        </a>
      ) : null}

      {result.deadline ? (
        <div className="flex gap-3 rounded-[22px] bg-card p-5">
          <CalendarClockIcon className="mt-0.5 size-5 shrink-0 text-vermilion" aria-hidden />
          <p className="text-sm leading-relaxed">
            {t('check.deadline', { body: result.deadline_body, date: formatDate(result.deadline) })}
            {left !== null && left >= 0 ? <b> {t('check.daysLeft', { count: left })}</b> : null}
          </p>
        </div>
      ) : null}

      {result.ladder?.length ? (
        <div className="rounded-[22px] bg-card p-5">
          <h2 className="text-sm font-bold">{t('check.steps')}</h2>
          <ol className="mt-3 flex flex-col gap-2">
            {result.ladder.map((s, i) => (
              <li key={s.step} className="flex gap-3 text-sm">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-accent text-xs font-bold text-brand">{i + 1}</span>
                <span>
                  <b>{s.step}</b> · {t('tracker.replyWithin', { days: s.deadline_days })}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 rounded-[24px] border border-line bg-surface p-5">
        <h2 className="font-display text-xl font-bold tracking-[-0.03em]">{t('check.ctaTitle')}</h2>
        <p className="text-sm text-muted-foreground">{t('check.ctaSub')}</p>
        <Button className="h-12" onClick={onBuild}>
          {t('check.cta')}
          <ArrowRightIcon aria-hidden />
        </Button>
        <button type="button" onClick={onReset} className="text-sm font-semibold text-brand">
          {t('check.another')}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">{t('check.disclaimer')}</p>
    </div>
  )
}

/** "STAR HEALTH AND ALLIED INSURANCE CO. LTD." -> "Star Health and Allied Insurance", for a headline. */
function prettyName(name: string | null | undefined): string | null {
  if (!name) return null
  const trimmed = name.replace(/\b(co\.?|company|ltd\.?|limited|pvt\.?|private)\b\.?/gi, '').replace(/[\s.,]+$/, '').trim()
  if (trimmed !== trimmed.toUpperCase()) return trimmed
  const small = new Set(['and', 'of', 'the'])
  return trimmed
    .toLowerCase()
    .split(/\s+/)
    .map((w, i) => (i > 0 && small.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ')
}
