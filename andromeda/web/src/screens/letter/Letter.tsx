import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckIcon, CopyIcon, DownloadIcon, PencilLineIcon, SendIcon } from 'lucide-react'
import { AppHeader, Button, EmptyState, FooterCTA, Input, Spinner } from '@/components'
import { useCase, useRedraftLetter } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { SUPPORTED_LANGUAGES } from '@/i18n'
import { downloadBlob } from '@/lib/download'
import { cn } from '@/lib/cn'

const TONES = [
  { key: 'firm', instruction: 'Make it firmer and more assertive, still polite.' },
  { key: 'friendly', instruction: 'Make it softer and more polite.' },
  { key: 'concise', instruction: 'Make it shorter and to the point.' },
  { key: 'detailed', instruction: 'Add more detail and cite every relevant clause.' },
] as const

const PLACEHOLDER = /\[[^\]\n]{2,60}\]/g

/** Placeholders like [Your Address] must be filled in before sending: highlight them. */
function Body({ text }: { text: string }) {
  const parts: (string | { hole: string })[] = []
  let last = 0
  for (const m of text.matchAll(PLACEHOLDER)) {
    parts.push(text.slice(last, m.index), { hole: m[0] })
    last = (m.index ?? 0) + m[0].length
  }
  parts.push(text.slice(last))
  return (
    <div className="whitespace-pre-line text-[15px] leading-relaxed">
      {parts.map((p, i) =>
        typeof p === 'string' ? (
          p
        ) : (
          <mark key={i} className="rounded bg-amber/25 px-0.5 font-semibold text-foreground">
            {p.hole}
          </mark>
        ),
      )}
    </div>
  )
}

export function Letter() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const redraft = useRedraftLetter(caseId ?? '')
  const [view, setView] = useState<'en' | 'local'>('en')
  const [busy, setBusy] = useState<string | null>(null)
  const [ask, setAsk] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const letter = kase?.letter
  if (!letter) {
    return (
      <div className="flex flex-col gap-6">
        <AppHeader title={t('letter.title')} />
        <EmptyState
          title={t('letter.notReady')}
          description={t('letter.notReadySub')}
          action={
            <button type="button" onClick={() => navigate(`/case/${caseId}/chances`)} className="text-brand underline">
              {t('chances.title')}
            </button>
          }
        />
      </div>
    )
  }

  const localLabel = SUPPORTED_LANGUAGES.find((l) => l.code === letter.language)?.label
  const hasLocal = Boolean(letter.local) && letter.language !== 'en'
  const active = view === 'local' && hasLocal ? 'local' : 'en'
  const body = active === 'local' ? (letter.local ?? letter.english) : letter.english
  const holes = [...new Set(body.match(PLACEHOLDER) ?? [])]

  async function rewrite(key: string, instruction: string) {
    setError(null)
    setBusy(key)
    try {
      await redraft.mutateAsync({ instruction })
      if (key === 'ask') setAsk('')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('letter.errorRedraft'))
    } finally {
      setBusy(null)
    }
  }

  async function download() {
    setError(null)
    try {
      downloadBlob(await apiBlob(`/cases/${caseId}/letter.pdf?local=${active === 'local'}`), 'appeal-letter.pdf')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('letter.errorDownload'))
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(`${letter!.subject}\n\n${body}`)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 pb-24">
      <AppHeader title={t('letter.title')} />

      <div className="sticky top-0 z-20 -mx-4 flex flex-col gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          {hasLocal ? (
            <div className="flex rounded-full border border-border p-0.5" role="tablist">
              {(['en', 'local'] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  role="tab"
                  aria-selected={active === v}
                  onClick={() => setView(v)}
                  className={cn(
                    'rounded-full px-3 py-1 text-sm font-semibold',
                    active === v ? 'bg-primary text-primary-foreground' : 'text-muted-foreground',
                  )}
                >
                  {v === 'en' ? 'English' : localLabel}
                </button>
              ))}
            </div>
          ) : null}
          <div className="ml-auto flex gap-1">
            <Button size="sm" variant="ghost" onClick={copy} aria-label={t('letter.copy')}>
              {copied ? <CheckIcon className="size-4 text-mint" /> : <CopyIcon className="size-4" />}
              <span className="hidden sm:inline">{copied ? t('letter.copied') : t('letter.copy')}</span>
            </Button>
            <Button size="sm" variant="outline" onClick={download}>
              <DownloadIcon className="size-4" aria-hidden />
              {t('letter.download')}
            </Button>
          </div>
        </div>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-0.5">
          {TONES.map((tone) => (
            <button
              key={tone.key}
              type="button"
              disabled={Boolean(busy)}
              onClick={() => rewrite(tone.key, tone.instruction)}
              className="flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-border bg-card px-3 text-sm disabled:opacity-50"
            >
              {busy === tone.key ? <Spinner /> : null}
              {t(`letter.toneOptions.${tone.key}`)}
            </button>
          ))}
        </div>
        <form
          className="flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault()
            if (ask.trim()) rewrite('ask', ask.trim())
          }}
        >
          <PencilLineIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <Input
            value={ask}
            onChange={(e) => setAsk(e.target.value)}
            placeholder={t('letter.askPlaceholder')}
            disabled={Boolean(busy)}
            className="h-9 flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
          />
          <Button type="submit" size="icon" variant="ghost" disabled={!ask.trim() || Boolean(busy)} aria-label={t('letter.askSend')}>
            {busy === 'ask' ? <Spinner /> : <SendIcon className="size-4" />}
          </Button>
        </form>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {holes.length ? (
        <section className="flex flex-col gap-2 rounded-xl border border-amber/50 bg-amber/10 p-4">
          <p className="text-sm font-semibold">{t('letter.fillIn', { count: holes.length })}</p>
          <div className="flex flex-wrap gap-1.5">
            {holes.map((h) => (
              <span key={h} className="rounded bg-amber/25 px-1.5 py-0.5 text-xs font-semibold">
                {h.slice(1, -1)}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <article className="relative rounded-xl border border-border bg-card px-5 py-6 shadow-sm sm:px-8">
        <p className="mb-4 border-b border-border pb-3 text-sm">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">{t('letter.subject')} </span>
          <span className="font-semibold">{letter.subject}</span>
        </p>
        <Body text={body} />
        {busy ? (
          <div className="absolute inset-0 grid place-items-center rounded-xl bg-card/80 backdrop-blur-[1px]">
            <span className="flex items-center gap-2 text-sm font-semibold">
              <Spinner /> {t('letter.rewriting')}
            </span>
          </div>
        ) : null}
      </article>

      <FooterCTA primary={{ label: t('letter.cta'), onClick: () => navigate(`/case/${caseId}/filing`) }} />
    </div>
  )
}
