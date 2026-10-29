import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  AlertTriangleIcon,
  ClipboardListIcon,
  DownloadIcon,
  FileTextIcon,
  GaugeIcon,
  LoaderCircleIcon,
  MailIcon,
  MessageCircleIcon,
  MessagesSquareIcon,
  MicIcon,
  PaperclipIcon,
  StethoscopeIcon,
  TrophyIcon,
  XIcon,
} from 'lucide-react'
import { Button, ErrorState, LanguageSwitcher, SourceKindIcon, Spinner, ThemeToggle } from '@/components'
import { apiBlob } from '@/api/client'
import { caseKey, useAnalyse, useCase, useDeleteDocument, usePack } from '@/api/hooks'
import { useLiveCase } from '@/api/live'
import type { CaseEvent, Document } from '@/api/types'
import { cn } from '@/lib/cn'
import { timeAgo } from '@/lib/dates'
import { downloadBlob } from '@/lib/download'
import { Composer } from './Composer'
import { NewClaim } from './NewClaim'
import { AnalysingPanel } from './Panels/AnalysingPanel'
import { ChancesPanel } from './Panels/ChancesPanel'
import { ConfirmingPayment } from './Panels/ConfirmingPayment'
import { DischargePanel } from './Panels/DischargePanel'
import { FilingPanel } from './Panels/FilingPanel'
import { LetterPanel } from './Panels/LetterPanel'
import { OutcomePanel } from './Panels/OutcomePanel'
import { SummaryPanel } from './Panels/SummaryPanel'
import { TrackerPanel } from './Panels/TrackerPanel'
import { UnlockPanel } from './Panels/UnlockPanel'
import { SectionDock, SectionList, type Section } from './SectionNav'
import { usePaymentReturn } from './usePaymentReturn'

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
  docs: Document[]
  onRemove: (id: string) => void
  canRemove: boolean
}) {
  const { t } = useTranslation()

  async function download(doc: Document) {
    try {
      const blob = await apiBlob(`/cases/${caseId}/documents/${doc.id}/file`)
      downloadBlob(blob, doc.filename)
    } catch {
      /* the preview already surfaces failures */
    }
  }

  if (!docs.length) return null
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-base font-bold">{t('workspace.files')}</h2>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {docs.map((d) => (
          <li key={d.id} className="flex flex-col gap-1.5">
            <div className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-2.5">
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
            </div>
            <div className="flex items-center justify-end gap-2 px-1">
              <button
                type="button"
                onClick={() => download(d)}
                aria-label={t('workspace.downloadFile', { name: d.filename })}
                className="grid size-6 place-items-center rounded-md text-muted-foreground transition-colors hover:text-brand"
              >
                <DownloadIcon className="size-4" aria-hidden />
              </button>
              {d.uploaded_at ? <span className="text-[11px] text-muted-foreground">{timeAgo(d.uploaded_at)}</span> : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function AnalyseBlock({
  failed,
  progress,
  error,
  isPending,
  onStart,
}: {
  failed: boolean
  progress?: string | null
  error: string | null
  isPending: boolean
  onStart: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-3">
      {failed ? (
        <div className="flex gap-3 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm">
          <AlertTriangleIcon className="mt-0.5 size-5 shrink-0 text-amber" aria-hidden />
          <p>{progress}</p>
        </div>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button onClick={onStart} loading={isPending} className="self-start">
        {failed ? t('upload.retry') : t('upload.analyse')}
      </Button>
    </div>
  )
}

function HearingBlock({ onStart, locked }: { onStart: () => void; locked: boolean }) {
  const { t } = useTranslation()
  return (
    <section className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <h2 className="font-display text-base font-bold">{t('hearing.title')}</h2>
        <p className="text-sm text-muted-foreground">
          {locked ? t('unlock.rehearsalLocked') : t('hearing.introSub')}
        </p>
      </div>
      <Button variant="outline" disabled={locked} onClick={onStart}>
        <MicIcon className="size-4" aria-hidden />
        {t('hearing.start')}
      </Button>
    </section>
  )
}

function QaFeed({ entries }: { entries: CaseEvent[] }) {
  const { t } = useTranslation()
  if (!entries.length) return null
  return (
    <section className="flex flex-col">
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
  const navigate = useNavigate()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: kase, error } = useCase(caseId)
  const { data: pack } = usePack(kase?.country)
  const live = useLiveCase(caseId)
  const analyse = useAnalyse(caseId ?? '')
  const remove = useDeleteDocument(caseId ?? '')
  const [analyseError, setAnalyseError] = useState<string | null>(null)
  const [active, setActive] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const prevStatus = useRef<string | undefined>(undefined)

  const current = (live.data ?? kase) ?? undefined
  const status = current?.status ?? 'collecting'
  // Stripe redirects back with ?paid=1 while its webhook is still landing. Show a confirming
  // state until paid_at appears, instead of asking the patient to pay a second time.
  const confirmingPayment = usePaymentReturn(caseId, Boolean(current?.paid_at))

  useEffect(() => {
    const prev = prevStatus.current
    prevStatus.current = status
    if (prev === 'analysing' && status === 'ready') setActive('summary')
    else if (prev !== 'resolved' && status === 'resolved') setActive('outcome')
  }, [status])

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

  const docs = current.documents ?? []
  const title = current.title || current.facts?.insurer || t('workspace.untitled')
  const hasAssessment = Boolean(current.assessment)
  // Payments on (the pack has a price) and this case not paid yet: PDFs and rehearsal are locked.
  const locked = Boolean(pack?.price_amount) && !current.paid_at
  const unlock =
    locked && pack ? (
      confirmingPayment ? (
        <ConfirmingPayment />
      ) : (
        <UnlockPanel caseId={caseId} price={pack} />
      )
    ) : null
  const discharge = current.kind === 'pre_discharge'
  const hasReport = Boolean(current.facts) && !discharge
  const failed = status === 'collecting' && Boolean(current.progress)
  const qa = (current.events ?? []).filter((e) => e.kind === 'message' || e.kind === 'ask')
  const empty = status === 'collecting' && docs.length === 0 && qa.length === 0 && !failed

  const sections: Section[] = []
  if (docs.length > 0) sections.push({ id: 'files', label: t('workspace.files'), icon: PaperclipIcon })
  if (status === 'analysing') sections.push({ id: 'analysing', label: t('upload.analysingHeading'), icon: LoaderCircleIcon })
  if (current.discharge_check) sections.push({ id: 'discharge', label: t('discharge.title'), icon: StethoscopeIcon })
  if (hasReport) sections.push({ id: 'summary', label: t('summary.title'), icon: FileTextIcon })
  if (hasAssessment) sections.push({ id: 'chances', label: t('chances.title'), icon: GaugeIcon })
  if (current.letter) sections.push({ id: 'letter', label: t('letter.title'), icon: MailIcon })
  if (hasAssessment) sections.push({ id: 'filing', label: t('filing.title'), icon: ClipboardListIcon })
  if (hasAssessment) sections.push({ id: 'tracker', label: t('tracker.title'), icon: ActivityIcon })
  if (hasAssessment && status !== 'resolved') sections.push({ id: 'hearing', label: t('hearing.title'), icon: MicIcon })
  if (status === 'resolved') sections.push({ id: 'outcome', label: t('outcome.title'), icon: TrophyIcon })
  if (qa.length > 0) sections.push({ id: 'conversation', label: t('workspace.conversation'), icon: MessagesSquareIcon })

  const preferred = current.discharge_check
    ? 'discharge'
    : status === 'resolved'
      ? 'outcome'
      : status === 'analysing'
        ? 'analysing'
        : status !== 'collecting'
          ? 'summary'
          : ''
  const activeId = active && sections.some((s) => s.id === active)
    ? active
    : preferred && sections.some((s) => s.id === preferred)
      ? preferred
      : (sections[0]?.id ?? '')

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

  const activeContent = (() => {
    switch (activeId) {
      case 'files':
        return (
          <>
            <FilesBlock
              caseId={caseId}
              docs={docs}
              onRemove={(id) => remove.mutate(id)}
              canRemove={status === 'collecting'}
            />
            {status === 'collecting' ? (
              <AnalyseBlock
                failed={failed}
                progress={current.progress}
                error={analyseError}
                isPending={analyse.isPending}
                onStart={startAnalyse}
              />
            ) : null}
          </>
        )
      case 'analysing':
        return <AnalysingPanel kase={current} />
      case 'discharge':
        return current.discharge_check ? <DischargePanel check={current.discharge_check} /> : null
      case 'summary':
        return <SummaryPanel kase={current} />
      case 'chances':
        return <ChancesPanel kase={current} />
      case 'letter':
        return (
          <>
            {unlock}
            <LetterPanel caseId={caseId} kase={current} locked={locked} />
          </>
        )
      case 'filing':
        return (
          <>
            {unlock}
            <FilingPanel caseId={caseId} kase={current} locked={locked} />
          </>
        )
      case 'tracker':
        return <TrackerPanel caseId={caseId} kase={current} />
      case 'hearing':
        return (
          <>
            {unlock}
            <HearingBlock locked={locked} onStart={() => navigate(`/case/${caseId}/hearing`)} />
          </>
        )
      case 'outcome':
        return <OutcomePanel caseId={caseId} kase={current} />
      case 'conversation':
        return <QaFeed entries={qa} />
      default:
        return null
    }
  })()

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-rule px-5 py-4 md:px-10">
        <div className="mx-auto w-full max-w-[760px]">{header}</div>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1">
          <div className="h-full overflow-y-auto">
            <div className="mx-auto w-full max-w-[760px] px-5 py-8 pb-32 md:px-10">
              <div className="flex flex-col gap-8">{activeContent}</div>
            </div>
          </div>

          <Composer
            caseId={caseId}
            kase={current}
            variant="dock"
            className={cn(
              'absolute inset-x-5 bottom-5 z-40 mx-auto max-w-[760px] transition-all duration-200 ease-out md:inset-x-10',
              chatOpen ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-3 opacity-0',
            )}
          />

          <button
            type="button"
            onClick={() => setChatOpen((o) => !o)}
            aria-label={chatOpen ? t('workspace.chat.close') : t('workspace.chat.open')}
            className={cn(
              'absolute right-4 bottom-4 z-50 grid size-12 place-items-center rounded-full bg-brand text-white shadow-float transition-all duration-200 hover:scale-105 lg:right-5 lg:bottom-5',
              chatOpen && 'bottom-24',
            )}
          >
            {chatOpen ? <XIcon className="size-5" aria-hidden /> : <MessageCircleIcon className="size-5" aria-hidden />}
          </button>

          <SectionDock sections={sections} active={activeId} onSelect={setActive} lifted={chatOpen} />
        </div>

        <aside className="hidden w-60 shrink-0 overflow-y-auto border-l border-rule px-3 py-6 lg:block">
          <p className="px-3 pb-2 font-display text-sm font-bold text-muted-foreground">{t('workspace.sections')}</p>
          <SectionList sections={sections} active={activeId} onSelect={setActive} />
        </aside>
      </div>
    </div>
  )
}