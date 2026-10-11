import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { MicIcon, PaperclipIcon, SendIcon } from 'lucide-react'
import { Button, ChatBubble, Input, Spinner } from '@/components'
import { caseKey, useAnalyse, useCase, useUploadDocument } from '@/api/hooks'
import { useLiveCase } from '@/api/live'

interface ChatMsg {
  id: string
  role: 'ai' | 'me'
  text?: string
  files?: string[]
}

export function Upload() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: kase } = useCase(caseId)
  const live = useLiveCase(caseId)
  const upload = useUploadDocument(caseId ?? '')
  const analyse = useAnalyse(caseId ?? '')

  const [messages, setMessages] = useState<ChatMsg[]>(() => [
    { id: 'welcome', role: 'ai', text: t('upload.greeting') },
  ])
  const [draft, setDraft] = useState('')
  const [analysing, setAnalysing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const idRef = useRef(0)
  const fileRef = useRef<HTMLInputElement>(null)
  const seenProgress = useRef<string[]>([])
  const readyAppended = useRef(false)
  const analysingRef = useRef(false)
  const sawAnalysingRef = useRef(false)

  const status = live.data?.status ?? kase?.status
  const docs = live.data?.documents ?? kase?.documents ?? []
  const hasDocs = docs.length > 0
  const inProgress = analysing || status === 'analysing'

  function append(msg: Omit<ChatMsg, 'id'>) {
    idRef.current += 1
    setMessages((m) => [...m, { ...msg, id: String(idRef.current) }])
  }

  // Each backend progress step arrives as a new assistant bubble ("live writing").
  useEffect(() => {
    const p = live.data?.progress
    if (p && !seenProgress.current.includes(p)) {
      seenProgress.current.push(p)
      append({ role: 'ai', text: p })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live.data?.progress])

  // Lifecycle: mark analysing seen, finish on ready, stop the spinner on failure.
  useEffect(() => {
    if (status === 'analysing') {
      sawAnalysingRef.current = true
    } else if (status === 'ready') {
      if (!readyAppended.current) {
        readyAppended.current = true
        analysingRef.current = false
        setAnalysing(false)
        const reason = live.data?.facts?.rejection_reason ?? kase?.facts?.rejection_reason ?? ''
        append({ role: 'ai', text: t('upload.done', { reason }) })
      }
    } else if (status === 'collecting' && sawAnalysingRef.current && analysingRef.current) {
      // The backend reset to `collecting` after a failed run — stop and offer a retry.
      analysingRef.current = false
      sawAnalysingRef.current = false
      setAnalysing(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  async function startAnalyse() {
    setAnalysing(true)
    analysingRef.current = true
    sawAnalysingRef.current = false
    setError(null)
    try {
      await analyse.mutateAsync()
    } catch (e) {
      analysingRef.current = false
      setAnalysing(false)
      setError(e instanceof Error ? e.message : t('upload.errorAnalyse'))
    }
  }

  async function handleFiles(files: File[]) {
    if (!files.length) return
    append({ role: 'me', files: files.map((f) => f.name) })
    setError(null)
    try {
      for (const f of files) await upload.mutateAsync(f)
      queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    } catch (e) {
      append({ role: 'ai', text: e instanceof Error ? e.message : t('upload.errorUpload') })
    }
  }

  function handleSend() {
    const text = draft.trim()
    if (!text) return
    append({ role: 'me', text })
    setDraft('')
    append({ role: 'ai', text: hasDocs ? t('upload.acknowledged') : t('upload.needDocs') })
  }

  const canAnalyse = hasDocs && !inProgress && status === 'collecting'

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 pb-20">
      <div className="flex flex-col gap-3">
        {messages.map((m) => (
          <ChatBubble key={m.id} role={m.role}>
            {m.files ? (
              <ul className="flex flex-col gap-1">
                {m.files.map((f) => (
                  <li key={f} className="font-mono text-xs">
                    {f}
                  </li>
                ))}
              </ul>
            ) : (
              m.text
            )}
          </ChatBubble>
        ))}

        {inProgress ? (
          <ChatBubble role="ai">
            <span className="flex items-center gap-2 text-muted-foreground">
              <Spinner />
              {t('upload.thinking')}
            </span>
          </ChatBubble>
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {canAnalyse ? (
          <Button className="self-start" onClick={startAnalyse} loading={analyse.isPending}>
            {t('upload.analyse')}
          </Button>
        ) : null}

        {status === 'ready' ? (
          <Button className="self-start" onClick={() => navigate(`/case/${caseId}/summary`)}>
            {t('upload.seeFull')}
          </Button>
        ) : null}
      </div>

      <div className="fixed inset-x-0 bottom-4 z-30 px-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="mx-auto flex w-full max-w-3xl items-center gap-1 rounded-full border border-border bg-card p-1.5 shadow-lg"
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
            aria-label={t('upload.voice')}
            title={t('upload.voice')}
          >
            <MicIcon className="size-5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="rounded-full"
            aria-label={t('upload.attach')}
            onClick={() => fileRef.current?.click()}
          >
            <PaperclipIcon className="size-5" />
          </Button>
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={t('upload.inputPlaceholder')}
            className="h-9 flex-1 border-0 bg-transparent px-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
          />
          <Button
            type="submit"
            size="icon"
            className="rounded-full"
            disabled={!draft.trim()}
            aria-label={t('upload.send')}
          >
            <SendIcon className="size-5" />
          </Button>
        </form>
      </div>
    </div>
  )
}