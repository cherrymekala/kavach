import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangleIcon, DownloadIcon } from 'lucide-react'
import { Button, Input, Label, Textarea } from '@/components'
import { useFiling, useSetComplainant } from '@/api/hooks'
import { apiBlob } from '@/api/client'
import { downloadBlob } from '@/lib/download'
import type { Case } from '@/api/types'

const EMPTY_FORM = { name: '', mobile: '', email: '', address: '', relationship: '' }

export function FilingPanel({
  caseId,
  kase,
  locked = false,
}: {
  caseId: string
  kase: Case
  /** Payments are on and the appeal pack is unpaid: the form PDF is not ours to download yet. */
  locked?: boolean
}) {
  const { t } = useTranslation()
  const setComplainant = useSetComplainant(caseId)
  const { data: filing } = useFiling(caseId, kase?.escalation_step)

  const [form, setForm] = useState(EMPTY_FORM)
  const [hydratedFor, setHydratedFor] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

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
      downloadBlob(await apiBlob(`/cases/${caseId}/filing.pdf`), 'filing-pack.pdf')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('filing.errorDownload'))
    }
  }

  const missing = filing?.missing ?? []

  return (
    <section className="flex flex-col gap-5">
      <header>
        <h2 className="font-display text-xl font-bold">{t('filing.title')}</h2>
      </header>

      <div className="grid items-start gap-8 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
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
              <Input id="f-rel" placeholder={t('filing.relationshipPlaceholder')} value={form.relationship} onChange={(e) => set('relationship', e.target.value)} />
            </div>
          </div>
          <Button onClick={handleSave} loading={setComplainant.isPending} className="self-start">
            {t('filing.save')}
          </Button>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-base font-bold">{t('filing.pack')}</h3>
            <Button
              size="sm"
              variant="outline"
              disabled={locked}
              title={locked ? t('unlock.downloadLocked') : undefined}
              onClick={handleDownload}
            >
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
          ) : null}
        </div>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </section>
  )
}