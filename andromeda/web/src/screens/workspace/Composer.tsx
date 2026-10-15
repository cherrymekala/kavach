import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { MicIcon, PaperclipIcon, SendIcon } from 'lucide-react'
import { Button, Input } from '@/components'
import { caseKey, useAddNote, useAsk, useUploadDocument } from '@/api/hooks'
import type { Case } from '@/api/types'
import { cn } from '@/lib/cn'

interface ComposerProps {
  caseId: string
  kase: Case
  variant?: 'hero' | 'dock'
  /** Extra classes for the dock wrapper (positioning, animation). */
  className?: string
}

/** The single input for everything: attach files, ask a question, or add a note. */
export function Composer({ caseId, kase, variant = 'dock', className }: ComposerProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const upload = useUploadDocument(caseId)
  const ask = useAsk(caseId)
  const note = useAddNote(caseId)

  const [text, setText] = useState('')
  const [uploading, setUploading] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const hasAssessment = Boolean(kase.assessment)
  const busy = ask.isPending || note.isPending || uploading.length > 0

  async function handleFiles(files: File[]) {
    if (!files.length) return
    setError(null)
    setUploading(files.map((f) => f.name))
    try {
      for (const f of files) await upload.mutateAsync(f)
      queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('upload.errorUpload'))
    } finally {
      setUploading([])
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const q = text.trim()
    if (!q || busy) return
    setText('')
    setError(null)
    try {
      if (hasAssessment) await ask.mutateAsync({ question: q })
      else await note.mutateAsync({ text: q })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('workspace.ask.error'))
    }
  }

  const input = (
    <form
      onSubmit={submit}
      className={cn(
        'flex items-center gap-1 rounded-full border border-line bg-surface shadow-sm',
        variant === 'hero' ? 'p-2' : 'p-1.5',
      )}
    >
      <input
        ref={fileRef}
        type="file"
        multiple
        accept="image/*,application/pdf,.txt"
        className="sr-only"
        onChange={(e) => {
          handleFiles(Array.from(e.target.files ?? []))
          e.target.value = ''
        }}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled
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
        loading={ask.isPending || note.isPending}
        aria-label={t('workspace.composer.send')}
      >
        {!(ask.isPending || note.isPending) ? <SendIcon className="size-4" /> : null}
      </Button>
    </form>
  )

  if (variant === 'hero') {
    return (
      <div className="flex w-full flex-col items-center gap-6 text-center">
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight">{t('workspace.composer.heroTitle')}</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{t('workspace.composer.heroSub')}</p>
        </div>
        <div className="w-full max-w-xl">{input}</div>
        <p className="font-mono text-xs text-muted-foreground">{t('upload.limits')}</p>
        {uploading.length ? <p className="text-sm text-muted-foreground">{uploading.join(', ')}…</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {input}
      {uploading.length ? <p className="px-2 text-xs text-muted-foreground">Uploading {uploading.join(', ')}…</p> : null}
      {error ? <p className="px-2 text-sm text-destructive">{error}</p> : null}
    </div>
  )
}