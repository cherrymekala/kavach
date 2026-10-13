import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckIcon, CopyIcon, DownloadIcon, PencilLineIcon, SendIcon } from 'lucide-react'
import { Button, Input, Spinner } from '@/components'
import { useRedraftLetter } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { SUPPORTED_LANGUAGES } from '@/i18n'
import { downloadBlob } from '@/lib/download'
import type { Case } from '@/api/types'
import { cn } from '@/lib/cn'

const TONES = [
  { key: 'firm', instruction: 'Make it firmer and more assertive, still polite.' },
  { key: 'friendly', instruction: 'Make it softer and more polite.' },
  { key: 'concise', instruction: 'Make it shorter and to the point.' },
  { key: 'detailed', instruction: 'Add more detail and cite every relevant clause.' },
] as const

const PLACEHOLDER = /\[[^\]\n]{2,60}\]/g

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

export function LetterPanel({ caseId, kase }: { caseId: string; kase: Case }) {
  const { t } = useTranslation()
  const redraft = useRedraftLetter(caseId)
  const letter = kase.letter

  const [view, setView] = useState<'en' | 'local'>('en')
  const [busy, setBusy] = useState<string | null>(null)
  const [ask, setAsk] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!letter) return null

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
    <section className="flex flex-col gap-4">
      <header className="flex items-center gap-2">
        <h2 className="font-display text-xl font-bold">{t('letter.title')}</h2>
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
      </header>

      {hasLocal ? (
        <div className="flex rounded-full border border-line p-0.5" role="tablist">
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

      <div className="flex gap-2 overflow-x-auto">
        {TONES.map((tone) => (
          <button
            key={tone.key}
            type="button"
            disabled={Boolean(busy)}
            onClick={() => rewrite(tone.key, tone.instruction)}
            className="flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-line bg-surface px-3 text-sm disabled:opacity-50"
          >
            {busy === tone.key ? <Spinner /> : null}
            {t(`letter.toneOptions.${tone.key}`)}
          </button>
        ))}
      </div>

      <form
        className="flex items-center gap-1 rounded-full border border-line bg-surface px-2 py-1"
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
          className="h-8 flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <Button type="submit" size="icon" variant="ghost" disabled={!ask.trim() || Boolean(busy)} aria-label={t('letter.askSend')}>
          {busy === 'ask' ? <Spinner /> : <SendIcon className="size-4" />}
        </Button>
      </form>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {holes.length ? (
        <div className="flex flex-col gap-2 rounded-lg border border-amber/50 bg-amber/10 p-4">
          <p className="text-sm font-semibold">{t('letter.fillIn', { count: holes.length })}</p>
          <div className="flex flex-wrap gap-1.5">
            {holes.map((h) => (
              <span key={h} className="rounded bg-amber/25 px-1.5 py-0.5 text-xs font-semibold">
                {h.slice(1, -1)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <article className="relative rounded-lg border border-line bg-surface px-5 py-6 sm:px-8">
        <p className="mb-4 border-b border-line pb-3 text-sm">
          <span className="font-semibold">{t('letter.subject')} </span>
          <span className="font-semibold">{letter.subject}</span>
        </p>
        <Body text={body} />
        {busy ? (
          <div className="absolute inset-0 grid place-items-center rounded-lg bg-surface/80 backdrop-blur-[1px]">
            <span className="flex items-center gap-2 text-sm font-semibold">
              <Spinner /> {t('letter.rewriting')}
            </span>
          </div>
        ) : null}
      </article>
    </section>
  )
}