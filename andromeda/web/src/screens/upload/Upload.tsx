import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangleIcon,
  CameraIcon,
  CheckIcon,
  CircleIcon,
  FileIcon,
  LoaderCircleIcon,
  UploadIcon,
  XIcon,
} from 'lucide-react'
import { AppHeader, FooterCTA, SourceKindIcon } from '@/components'
import { caseKey, useAnalyse, useCase, useDeleteDocument, useUploadDocument } from '@/api/hooks'
import { useLiveCase } from '@/api/live'
import { cn } from '@/lib/cn'

/** The pipeline's progress messages, in order (sombrero/src/kavach/agents/orchestrator.py). */
const STEPS = [
  'Reading your documents',
  'Decoding the rejection',
  'Finding the rules that apply',
  'Looking up similar past cases',
  'Building your case',
  'Checking every source',
  'Writing your appeal',
] as const

const WANTED = ['rejection_letter', 'policy', 'discharge_summary'] as const
const ACCEPT = 'image/*,application/pdf,.txt'

function Steps({ current }: { current: string | null | undefined }) {
  const { t } = useTranslation()
  const at = current ? STEPS.indexOf(current as (typeof STEPS)[number]) : 0
  return (
    <ol className="flex flex-col">
      {STEPS.map((step, i) => {
        const done = i < at
        const active = i === Math.max(at, 0)
        return (
          <li key={step} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'grid size-7 place-items-center rounded-full border-2',
                  done && 'border-mint bg-mint text-white',
                  active && 'border-brand text-brand',
                  !done && !active && 'border-border text-muted-foreground',
                )}
              >
                {done ? (
                  <CheckIcon className="size-4" aria-hidden />
                ) : active ? (
                  <LoaderCircleIcon className="size-4 animate-spin" aria-hidden />
                ) : (
                  <CircleIcon className="size-2 fill-current" aria-hidden />
                )}
              </span>
              {i < STEPS.length - 1 ? (
                <span className={cn('my-1 w-0.5 flex-1', done ? 'bg-mint' : 'bg-border')} />
              ) : null}
            </div>
            <div className={cn('pb-5 pt-0.5', !done && !active && 'text-muted-foreground')}>
              <p className={cn('text-sm', active && 'font-semibold')}>{t(`upload.steps.${i}.label`)}</p>
              {active ? <p className="text-xs text-muted-foreground">{t(`upload.steps.${i}.detail`)}</p> : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export function Upload() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: kase } = useCase(caseId)
  const live = useLiveCase(caseId)
  const upload = useUploadDocument(caseId ?? '')
  const remove = useDeleteDocument(caseId ?? '')
  const analyse = useAnalyse(caseId ?? '')

  const [uploading, setUploading] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const cameraRef = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  const current = live.data ?? kase
  const status = current?.status
  const progress = current?.progress
  const docs = current?.documents ?? []
  const analysing = status === 'analysing' || (started && status === 'collecting' && !progress)
  // A run that ends back in `collecting` with a message failed (e.g. no rejection letter found).
  const failed = status === 'collecting' && Boolean(progress) && !STEPS.includes(progress as (typeof STEPS)[number])

  useEffect(() => {
    if (status === 'ready' && started) navigate(`/case/${caseId}/summary`)
  }, [status, started, caseId, navigate])

  async function addFiles(files: File[]) {
    if (!files.length) return
    setError(null)
    setUploading(files.map((f) => f.name))
    try {
      for (const f of files) await upload.mutateAsync(f)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('upload.errorUpload'))
    } finally {
      setUploading([])
      queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    }
  }

  async function start() {
    setError(null)
    setStarted(true)
    try {
      await analyse.mutateAsync()
      queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    } catch (e) {
      setStarted(false)
      setError(e instanceof Error ? e.message : t('upload.errorAnalyse'))
    }
  }

  if (analysing) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-12">
        <AppHeader title={t('upload.analysingHeading')} />
        <p className="-mt-3 text-sm text-muted-foreground">{t('upload.analysingSub')}</p>
        <section className="rounded-2xl border border-border bg-card p-5">
          <Steps current={progress} />
        </section>
      </div>
    )
  }

  const canAnalyse = docs.length > 0 && uploading.length === 0 && status === 'collecting'

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pb-24">
      <AppHeader title={t('upload.heading')} />
      <p className="-mt-3 text-sm text-muted-foreground">{t('upload.sub')}</p>

      {failed ? (
        <div className="flex gap-3 rounded-xl border border-amber/50 bg-amber/10 p-4 text-sm">
          <AlertTriangleIcon className="mt-0.5 size-5 shrink-0 text-amber" aria-hidden />
          <p>{progress}</p>
        </div>
      ) : null}

      <ul className="grid gap-2 sm:grid-cols-3">
        {WANTED.map((kind) => (
          <li key={kind} className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
              <SourceKindIcon kind={kind} />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold">{t(`upload.wanted.${kind}.label`)}</p>
              <p className="text-xs text-muted-foreground">{t(`upload.wanted.${kind}.hint`)}</p>
            </div>
          </li>
        ))}
      </ul>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          addFiles(Array.from(e.dataTransfer.files))
        }}
        className={cn(
          'flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-border p-6 text-center',
          over && 'border-brand bg-accent/50',
        )}
      >
        <UploadIcon className="size-7 text-muted-foreground" aria-hidden />
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex h-11 items-center justify-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground"
          >
            <FileIcon className="size-4" aria-hidden />
            {t('upload.choose')}
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            className="flex h-11 items-center justify-center gap-2 rounded-full border border-border bg-card px-5 text-sm font-semibold"
          >
            <CameraIcon className="size-4" aria-hidden />
            {t('upload.photo')}
          </button>
        </div>
        <p className="font-mono text-xs text-muted-foreground">{t('upload.limits')}</p>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            addFiles(Array.from(e.target.files ?? []))
            e.target.value = ''
          }}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          onChange={(e) => {
            addFiles(Array.from(e.target.files ?? []))
            e.target.value = ''
          }}
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {docs.length || uploading.length ? (
        <section className="flex flex-col gap-2">
          <h3 className="font-display text-base font-bold">{t('upload.yourFiles', { count: docs.length })}</h3>
          <ul className="flex flex-col gap-2">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
                <SourceKindIcon kind={d.doc_type ?? 'other'} className="size-5 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate text-sm">{d.filename}</span>
                {status === 'collecting' ? (
                  <button
                    type="button"
                    onClick={() => remove.mutate(d.id)}
                    aria-label={t('upload.remove', { name: d.filename })}
                    className="grid size-8 place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <XIcon className="size-4" aria-hidden />
                  </button>
                ) : null}
              </li>
            ))}
            {uploading.map((name) => (
              <li
                key={`up-${name}`}
                className="flex items-center gap-3 rounded-xl border border-dashed border-border p-3 text-muted-foreground"
              >
                <LoaderCircleIcon className="size-5 animate-spin" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm">{name}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <FooterCTA
        primary={
          status === 'ready'
            ? { label: t('upload.seeFull'), onClick: () => navigate(`/case/${caseId}/summary`) }
            : {
                label: failed ? t('upload.retry') : t('upload.analyse'),
                onClick: start,
                disabled: !canAnalyse,
                loading: analyse.isPending,
              }
        }
      />
    </div>
  )
}
