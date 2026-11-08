import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { MicIcon, PaperclipIcon, SendIcon } from 'lucide-react'
import { Button, Input } from '@/components'
import { apiFetch } from '@/api/client'
import { caseKey, useCreateCase } from '@/api/hooks'
import type { CaseKind, CreateCase } from '@/api/types'

// Heading and lead for each kind of case the patient can start.
const HERO: Record<string, [string, string]> = {
  dispute: ['workspace.composer.heroTitle', 'workspace.composer.heroSub'],
  pre_discharge: ['discharge.heroTitle', 'discharge.heroSub'],
  preauth: ['preauth.heroTitle', 'preauth.heroSub'],
}
import { useAuth } from '@/auth'
import { COUNTRIES, countryFromPhone, type CountryCode } from '@/lib/country'
import { cn } from '@/lib/cn'

/** The "new claim" composer shown when no case is selected — creates a case on first action. */
export function NewClaim() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const createCase = useCreateCase()
  const queryClient = useQueryClient()

  const [country, setCountry] = useState<CountryCode>(countryFromPhone(user?.phoneNumber))
  const [kind, setKind] = useState<CaseKind>('dispute')
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function begin(run: (caseId: string) => Promise<void>, query = '') {
    setError(null)
    setBusy(true)
    try {
      // `kind` is newer than the generated CreateCase type.
      const body = { country, language: i18n.language, kind } as CreateCase
      const c = await createCase.mutateAsync(body)
      await run(c.id)
      // Drop the cached (empty) case so the dossier fetches the note/files we just added.
      queryClient.removeQueries({ queryKey: caseKey(c.id) })
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      navigate(`/case/${c.id}${query}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('start.errorCreate'))
    } finally {
      setBusy(false)
    }
  }

  async function onFiles(files: File[]) {
    if (!files.length || busy) return
    await begin(async (id) => {
      for (const f of files) {
        const form = new FormData()
        form.append('file', f)
        await apiFetch(`/cases/${id}/documents`, { method: 'POST', body: form })
      }
    })
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = text.trim()
    if (!q || busy) return
    setText('')
    await begin(async (id) => {
      await apiFetch(`/cases/${id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: q }),
      })
    })
  }

  return (
    <div className="flex w-full flex-col items-center gap-6 text-center">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          {t(HERO[kind][0])}
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          {t(HERO[kind][1])}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-1 rounded-[22px] border border-line bg-surface p-0.5" role="group" aria-label={t('discharge.modeLabel')}>
        {(['dispute', 'preauth', 'pre_discharge'] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setKind(k)}
            aria-pressed={kind === k}
            className={cn(
              'rounded-full px-3 py-1 text-sm font-semibold',
              kind === k ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {t(k === 'preauth' ? 'preauth.mode' : `discharge.mode.${k}`)}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1 rounded-full border border-line bg-surface p-0.5" role="group" aria-label="Country">
        {COUNTRIES.map((c) => (
          <button
            key={c.code}
            type="button"
            onClick={() => setCountry(c.code)}
            aria-pressed={country === c.code}
            className={cn(
              'rounded-full px-3 py-1 text-sm font-semibold',
              country === c.code ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {c.name}
          </button>
        ))}
      </div>

      <form
        onSubmit={onSubmit}
        className="flex w-full max-w-xl items-center gap-1 rounded-full border border-line bg-surface p-2 shadow-sm"
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/*,application/pdf,.txt"
          className="sr-only"
          onChange={(e) => {
            onFiles(Array.from(e.target.files ?? []))
            e.target.value = ''
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={busy}
          onClick={() => begin(async () => {}, '?voice=1')}
          className="rounded-full"
          aria-label={t('workspace.composer.mic')}
          title={t('workspace.composer.mic')}
        >
          <MicIcon className="size-5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label={t('workspace.composer.attach')}
          onClick={() => fileRef.current?.click()}
        >
          <PaperclipIcon className="size-5" />
        </Button>
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('workspace.composer.placeholder')}
          className="h-9 flex-1 border-0 bg-transparent px-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <Button
          type="submit"
          size="icon"
          className="rounded-full"
          disabled={!text.trim() || busy}
          loading={busy}
          aria-label={t('workspace.composer.send')}
        >
          {!busy ? <SendIcon className="size-4" /> : null}
        </Button>
      </form>

      <Button variant="outline" className="h-11" disabled={busy} onClick={() => begin(async () => {}, '?voice=1')}>
        <MicIcon aria-hidden />
        {t('voice.start')}
      </Button>

      <p className="text-xs text-muted-foreground">{t('upload.limits')}</p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  )
}