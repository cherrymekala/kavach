import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { AlertTriangleIcon, XIcon } from 'lucide-react'
import { Button, ErrorState, LanguageSwitcher, SourceKindIcon, Spinner, ThemeToggle } from '@/components'
import { apiBlob } from '@/api/client'
import { caseKey, useAnalyse, useCase, useDeleteDocument } from '@/api/hooks'
import { useLiveCase } from '@/api/live'
import type { Case, CaseEvent, Document, WithTitle } from '@/api/types'
import { cn } from '@/lib/cn'
import { Composer } from './Composer'
import { NewClaim } from './NewClaim'
import { AnalysingPanel } from './Panels/AnalysingPanel'
import { ChancesPanel } from './Panels/ChancesPanel'
import { FilingPanel } from './Panels/FilingPanel'
import { LetterPanel } from './Panels/LetterPanel'
import { OutcomePanel } from './Panels/OutcomePanel'
import { SummaryPanel } from './Panels/SummaryPanel'
import { TrackerPanel } from './Panels/TrackerPanel'

const DOT: Record<string, string> = {
  ready: 'bg-mint',
  resolved: 'bg-mint',
  analysing: 'bg-amber',
  filed: 'bg-amber',
  escalated: 'bg-amber',
  collecting: 'bg-muted-foreground/50',
}

function StatusLine({ status }: { status: string }) {
  const { t } = useTranslation()
  return (
    <span className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
      <span className={cn('size-2 rounded-full', DOT[status] ?? 'bg-muted-foreground/50', status === 'analysing' && 'animate-pulse')} />
      {t(`workspace.status.${status}`, { defaultValue: status })}
    </span>
  )
}

function FilePreview({ caseId, doc }: { caseId: string; doc: Document }) {
  const [url, setUrl] = useState<string | null>(null)
  const isImage = /\.(png|jpe?g|webp)$/i.test(doc.filename)

  useEffect(() => {
    if (!isImage) return
    let alive = true
    let objectUrl: string | null = null
    apiBlob(`/cases/${caseId}/documents/${doc.id}/file`)
      .then((b) => {
        if (!alive) return
        objectUrl = URL.createObjectURL(b)
        setUrl(objectUrl)
      })
      .catch(() => {})
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [caseId, doc.id, isImage])

  if (isImage && url) {
    return <img src={url} alt={doc.filename} className="h-32 w-full rounded-md border border-line object-cover" />
  }
  return (
    <div className="flex h-32 w-full items-center justify-center rounded-md border border-line bg-muted/50">
      <SourceKindIcon kind={doc.doc_type ?? 'other'} className="size-8 text-muted-foreground" />
    </div>
  )
}

function FilesBlock({
  caseId,
  docs,
  onRemove,
  canRemove,
}: {
  caseId: string
  docs: Case['documents']
  onRemove: (id: string) => void
  canRemove: boolean
}) {
  const { t } = useTranslation()
  if (!docs.length) return null
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-base font-bold">{t('workspace.files')}</h2>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {docs.map((d) => (
          <li key={d.id} className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-2.5">
            <FilePreview caseId={caseId} doc={d} />
            <div className="flex items-start gap-2 px-0.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{d.filename}</p>
                {d.warning ? (
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-amber">
                    <AlertTriangleIcon className="size-3 shrink-0" aria-hidden />
                    <span className="truncate">{d.warning}</span>
                  </p>
                ) : null}
              </div>
              {canRemove ? (
                <button
                  type="button"
                  onClick={() => onRemove(d.id)}
                  aria-label={t('upload.remove', { name: d.filename })}
                  className="grid size-7 shrink-0 place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <XIcon className="size-4" aria-hidden />
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function QaFeed({ entries }: { entries: CaseEvent[] }) {
  const { t } = useTranslation()
  if (!entries.length) return null
  return (
    <section className="border-t border-rule pt-6">
      <h2 className="font-display text-base font-bold">{t('workspace.conversation')}</h2>
      <div className="mt-3 flex flex-col">
        {entries.map((e, i) => (
          <div key={`${e.at}-${i}`} className="border-b border-rule/60 py-3 last:border-0">
            <p className="text-xs font-medium text-muted-foreground">
              {e.kind === 'message' ? t('workspace.you') : 'Kavach'}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{e.text}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export function Dossier() {
  const { caseId } = useParams()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: kase, error } = useCase(caseId)
  const live = useLiveCase(caseId)
  const analyse = useAnalyse(caseId ?? '')
  const remove = useDeleteDocument(caseId ?? '')
  const [analyseError, setAnalyseError] = useState<string | null>(null)

  if (!caseId) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-end gap-1 px-5 pt-4">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
        <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto px-5 pb-10">
          <NewClaim />
        </div>
      </div>
    )
  }

  const current = ((live.data ?? kase) as (Case & WithTitle) | undefined) ?? undefined
  if (!current) {
    if (error) {
      return (
        <div className="grid h-full place-items-center px-6">
          <ErrorState title={t('workspace.loadError')} message={error.message} />
        </div>
      )
    }
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner />
      </div>
    )
  }

  const status = current?.status ?? 'collecting'
  const docs = current?.documents ?? []
  const title = current?.title || current?.facts?.insurer || t('workspace.untitled')
  const hasAssessment = Boolean(current?.assessment)
  const hasReport = Boolean(current?.facts)
  const failed = status === 'collecting' && Boolean(current?.progress)
  const qa = (current?.events ?? []).filter((e) => e.kind === 'message' || e.kind === 'ask')
  const empty = status === 'collecting' && docs.length === 0 && qa.length === 0 && !failed

  const header = (
    <header className="flex items-center gap-3">
      <h1 className="min-w-0 flex-1 truncate font-display text-2xl font-bold tracking-tight">{title}</h1>
      <LanguageSwitcher />
      <ThemeToggle />
      <StatusLine status={status} />
    </header>
  )

  async function startAnalyse() {
    setAnalyseError(null)
    try {
      await analyse.mutateAsync()
      queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    } catch (e) {
      setAnalyseError(e instanceof Error ? e.message : t('upload.errorAnalyse'))
    }
  }

  if (empty) {
    return (
      <div className="flex h-full flex-col">
        <div className="px-5 pt-8 md:px-10">
          <div className="mx-auto w-full max-w-[760px]">{header}</div>
        </div>
        <div className="flex min-h-0 flex-1 items-center justify-center px-5 pb-10">
          <Composer caseId={caseId} kase={current} variant="hero" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[760px] px-5 py-8 md:px-10">
          {header}

          <div className="mt-6 flex flex-col gap-8">
            <FilesBlock caseId={caseId} docs={docs} onRemove={(id) => remove.mutate(id)} canRemove={status === 'collecting'} />

            {status === 'collecting' && docs.length > 0 ? (
              <div className="flex flex-col gap-3">
                {failed ? (
                  <div className="flex gap-3 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm">
                    <AlertTriangleIcon className="mt-0.5 size-5 shrink-0 text-amber" aria-hidden />
                    <p>{current?.progress}</p>
                  </div>
                ) : null}
                {analyseError ? <p className="text-sm text-destructive">{analyseError}</p> : null}
                <Button onClick={startAnalyse} loading={analyse.isPending} className="self-start">
                  {failed ? t('upload.retry') : t('upload.analyse')}
                </Button>
              </div>
            ) : null}

            {status === 'analysing' && current ? <AnalysingPanel kase={current} /> : null}

            {hasReport && current ? <SummaryPanel kase={current} /> : null}
            {hasAssessment && current ? <ChancesPanel kase={current} /> : null}
            {current?.letter ? <LetterPanel caseId={caseId} kase={current} /> : null}
            {hasAssessment && current ? <FilingPanel caseId={caseId} kase={current} /> : null}
            {hasAssessment && current ? <TrackerPanel caseId={caseId} kase={current} /> : null}
            {status === 'resolved' && current ? <OutcomePanel caseId={caseId} kase={current} /> : null}

            <QaFeed entries={qa} />
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t border-line bg-page px-4 py-3">
        <div className="mx-auto w-full max-w-[760px]">
          <Composer caseId={caseId} kase={current} variant="dock" />
        </div>
      </div>
    </div>
  )
}