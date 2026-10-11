import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckCircle2Icon, DownloadIcon, Trash2Icon } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AppHeader,
  Button,
  FooterCTA,
} from '@/components'
import { useCase, useDeleteCase } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { downloadBlob } from '@/lib/download'
import { formatMoney } from '@/lib/money'

export function Outcome() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const deleteCase = useDeleteCase()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  const recovered = kase?.amount_recovered
  const currency = kase?.country === 'SG' ? 'SGD' : 'INR'

  async function handleDownload(path: string, name: string) {
    try {
      const blob = await apiBlob(path)
      downloadBlob(blob, name)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('outcome.errorDownload'))
    }
  }

  async function handleDelete() {
    setError(null)
    try {
      await deleteCase.mutateAsync(caseId ?? '')
      navigate('/start', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('outcome.errorDelete'))
      setConfirmOpen(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <AppHeader title={t('outcome.title')} />

      <section className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-card p-8 text-center">
        <span className="grid size-14 place-items-center rounded-full bg-mint/15 text-mint">
          <CheckCircle2Icon className="size-7" aria-hidden />
        </span>
        <h2 className="font-display text-2xl font-extrabold">{t('outcome.congrats')}</h2>
        {recovered != null ? (
          <div className="mt-1">
            <p className="text-sm text-muted-foreground">{t('outcome.recovered')}</p>
            <p className="font-display text-3xl font-extrabold text-mint">{formatMoney(recovered, currency)}</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t('outcome.sub')}</p>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="font-display text-base font-bold">{t('outcome.download')}</h3>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => handleDownload(`/cases/${caseId}/letter.pdf`, 'appeal-letter.pdf')}>
            <DownloadIcon className="size-4" aria-hidden />
            {t('letter.title')}
          </Button>
          <Button variant="outline" onClick={() => handleDownload(`/cases/${caseId}/filing.pdf`, 'filing-pack.pdf')}>
            <DownloadIcon className="size-4" aria-hidden />
            {t('filing.pack')}
          </Button>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 p-5">
        <h3 className="font-display text-base font-bold text-destructive">{t('outcome.deleteTitle')}</h3>
        <p className="text-sm text-muted-foreground">{t('outcome.deleteSub')}</p>
        <Button variant="destructive" className="self-start" onClick={() => setConfirmOpen(true)}>
          <Trash2Icon className="size-4" aria-hidden />
          {t('outcome.delete')}
        </Button>
      </section>

      <FooterCTA
        primary={{ label: t('outcome.cta'), onClick: () => navigate('/start') }}
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('outcome.deleteConfirm')}</AlertDialogTitle>
            <AlertDialogDescription>{t('outcome.deleteConfirmSub')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <Button variant="destructive" onClick={handleDelete} loading={deleteCase.isPending}>
              {t('outcome.delete')}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}