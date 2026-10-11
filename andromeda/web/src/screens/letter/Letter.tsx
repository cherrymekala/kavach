import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { DownloadIcon } from 'lucide-react'
import { AppHeader, Button, EmptyState, FooterCTA } from '@/components'
import { useCase, useRedraftLetter } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { downloadBlob } from '@/lib/download'
import { cn } from '@/lib/cn'

const TONES = [
  { key: 'friendly', instruction: 'Make it softer and more polite.' },
  { key: 'firm', instruction: 'Make it firmer and more assertive.' },
  { key: 'concise', instruction: 'Make it shorter and to the point.' },
  { key: 'detailed', instruction: 'Add more detail and cite every relevant clause.' },
] as const

export function Letter() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const redraft = useRedraftLetter(caseId ?? '')
  const [view, setView] = useState<'en' | 'local'>('en')
  const [tone, setTone] = useState<string | null>(null)
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
            <button
              type="button"
              onClick={() => navigate(`/case/${caseId}/chances`)}
              className="text-brand underline"
            >
              {t('chances.title')}
            </button>
          }
        />
      </div>
    )
  }

  const hasLocal = Boolean(letter.local)
  const activeView = view === 'local' && hasLocal ? 'local' : 'en'
  const body = activeView === 'local' ? (letter.local ?? letter.english) : letter.english

  async function handleRedraft(instruction: string) {
    setError(null)
    setTone(instruction)
    try {
      await redraft.mutateAsync({ instruction })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('letter.errorRedraft'))
    } finally {
      setTone(null)
    }
  }

  async function handleDownload() {
    try {
      const blob = await apiBlob(`/cases/${caseId}/letter.pdf?local=${activeView === 'local'}`)
      downloadBlob(blob, 'appeal-letter.pdf')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('letter.errorDownload'))
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <AppHeader title={t('letter.title')} />

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={activeView === 'en' ? 'default' : 'outline'}
          onClick={() => setView('en')}
        >
          {t('letter.english')}
        </Button>
        {hasLocal ? (
          <Button
            size="sm"
            variant={activeView === 'local' ? 'default' : 'outline'}
            onClick={() => setView('local')}
          >
            {t('letter.local')}
          </Button>
        ) : null}
        <Button size="sm" variant="ghost" className="ml-auto" onClick={handleDownload}>
          <DownloadIcon className="size-4" aria-hidden />
          {t('letter.download')}
        </Button>
      </div>

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <h3 className="font-display text-base font-bold">{letter.subject}</h3>
        <div className="whitespace-pre-line text-sm leading-relaxed">{body}</div>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="font-display text-base font-bold">{t('letter.tone')}</h3>
        <div className="flex flex-wrap gap-2">
          {TONES.map((toneItem) => (
            <Button
              key={toneItem.key}
              size="sm"
              variant="outline"
              className={cn(tone === toneItem.instruction && 'border-brand text-brand')}
              loading={redraft.isPending && tone === toneItem.instruction}
              onClick={() => handleRedraft(toneItem.instruction)}
            >
              {t(`letter.toneOptions.${toneItem.key}`)}
            </Button>
          ))}
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </section>

      <FooterCTA
        primary={{ label: t('letter.cta'), onClick: () => navigate(`/case/${caseId}/filing`) }}
      />
    </div>
  )
}