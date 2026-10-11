import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangleIcon, DownloadIcon } from 'lucide-react'
import { AppHeader, Button, EmptyState, FooterCTA, Input, Label, Textarea } from '@/components'
import { useCase, useFiling, useSetComplainant } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { downloadBlob } from '@/lib/download'

const EMPTY_FORM = {
  name: '',
  mobile: '',
  email: '',
  address: '',
  relationship: '',
}

export function Filing() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { data: kase, isLoading } = useCase(caseId)
  const setComplainant = useSetComplainant(caseId ?? '')
  const { data: filing } = useFiling(caseId ?? '', kase?.escalation_step)

  const [form, setForm] = useState(EMPTY_FORM)
  const [hydratedFor, setHydratedFor] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Derive the form from the loaded case once; don't re-clobber the user's edits.
  if (kase && hydratedFor !== kase.id) {
    setHydratedFor(kase.id)
    setForm({
      name: kase.complainant?.name ?? '',
      mobile: kase.complainant?.mobile ?? '',
      email: kase.complainant?.email ?? '',
      address: kase.complainant?.address ?? '',
      relationship: kase.complainant?.relationship_to_insured ?? '',
    })
  }

  if (isLoading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSave() {
    setError(null)
    try {
      await setComplainant.mutateAsync({
        name: form.name,
        mobile: form.mobile,
        email: form.email,
        address: form.address,
        relationship_to_insured: form.relationship,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('filing.errorSave'))
    }
  }

  async function handleDownload() {
    try {
      const blob = await apiBlob(`/cases/${caseId}/filing.pdf`)
      downloadBlob(blob, 'filing-pack.pdf')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('filing.errorDownload'))
    }
  }

  const missing = filing?.missing ?? []

  return (
    <div className="flex flex-col gap-6">
      <AppHeader title={t('filing.title')} />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
          <h3 className="font-display text-base font-bold">{t('filing.yourDetails')}</h3>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-name">{t('filing.name')}</Label>
              <Input id="f-name" value={form.name} onChange={(e) => set('name', e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="f-mobile">{t('filing.mobile')}</Label>
                <Input id="f-mobile" value={form.mobile} onChange={(e) => set('mobile', e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="f-email">{t('filing.email')}</Label>
                <Input id="f-email" type="email" value={form.email} onChange={(e) => set('email', e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-address">{t('filing.address')}</Label>
              <Textarea id="f-address" rows={2} value={form.address} onChange={(e) => set('address', e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-rel">{t('filing.relationship')}</Label>
              <Input
                id="f-rel"
                placeholder={t('filing.relationshipPlaceholder')}
                value={form.relationship}
                onChange={(e) => set('relationship', e.target.value)}
              />
            </div>
          </div>
          <Button onClick={handleSave} loading={setComplainant.isPending} className="self-start">
            {t('filing.save')}
          </Button>
        </section>

        <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-base font-bold">{t('filing.pack')}</h3>
            <Button size="sm" variant="outline" onClick={handleDownload}>
              <DownloadIcon className="size-4" aria-hidden />
              {t('filing.download')}
            </Button>
          </div>

          {filing ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-muted-foreground">
                {t('filing.disputeBody')}: <span className="font-medium text-foreground">{filing.dispute_body}</span>
              </p>
              {missing.length ? (
                <div className="flex flex-col gap-2 rounded-lg bg-amber/10 p-3">
                  <p className="flex items-center gap-2 text-sm font-semibold text-amber">
                    <AlertTriangleIcon className="size-4" aria-hidden />
                    {t('filing.missing')}
                  </p>
                  <ul className="flex flex-col gap-1 pl-6 text-sm">
                    {missing.map((m) => (
                      <li key={m} className="list-disc">
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-mint">{t('filing.complete')}</p>
              )}
            </div>
          ) : (
            <EmptyState title={t('filing.notReady')} description={t('filing.notReadySub')} />
          )}
        </section>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <FooterCTA
        primary={{ label: t('filing.cta'), onClick: () => navigate(`/case/${caseId}/hearing`) }}
      />
    </div>
  )
}