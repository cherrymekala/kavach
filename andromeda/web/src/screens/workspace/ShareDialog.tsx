import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckIcon, CopyIcon, UserRoundIcon } from 'lucide-react'
import { Button, Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components'
import { useCreateShareCode, useRemoveHelper } from '@/api/hooks'
import type { Case, ShareCode } from '@/api/types'
import { formatDate } from '@/lib/dates'

/**
 * Helper mode, patient side: make a one-time code for a caregiver, hospital desk or NGO, and
 * see or remove the people who can help with this case. Only the owner sees this.
 */
export function ShareDialog({ kase, open, onClose }: { kase: Case; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const create = useCreateShareCode(kase.id)
  const remove = useRemoveHelper(kase.id)
  const [share, setShare] = useState<ShareCode | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const helpers = kase.helpers ?? []
  const link = share ? `${window.location.origin}/join/${share.code}` : ''

  async function makeCode() {
    setError(null)
    try {
      setShare(await create.mutateAsync())
    } catch (e) {
      setError(e instanceof Error ? e.message : t('share.error'))
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(t('share.message', { code: share!.code, link }))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('share.title')}</DialogTitle>
          <DialogDescription>{t('share.sub')}</DialogDescription>
        </DialogHeader>

        <div className="flex min-w-0 flex-col gap-5">
          {share ? (
            <div className="flex min-w-0 flex-col items-center gap-3 rounded-[22px] bg-accent p-5 text-center">
              <p className="text-sm text-accent-foreground">{t('share.codeLabel')}</p>
              <p className="font-display text-[1.75rem] font-bold tracking-[0.06em] tabular-nums sm:text-4xl" aria-live="polite">
                {share.code}
              </p>
              <p className="text-xs text-muted-foreground">{t('share.expires', { date: formatDate(share.expires_at) })}</p>
              <Button variant="outline" onClick={copy}>
                {copied ? <CheckIcon className="text-mint" aria-hidden /> : <CopyIcon aria-hidden />}
                {copied ? t('letter.copied') : t('share.copy')}
              </Button>
            </div>
          ) : (
            <Button onClick={makeCode} loading={create.isPending} className="self-start">
              {t('share.create')}
            </Button>
          )}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-bold">{t('share.helpers')}</h3>
            {helpers.length ? (
              <ul className="flex flex-col gap-2">
                {helpers.map((h) => (
                  <li key={h.uid} className="flex items-center gap-3 rounded-2xl bg-muted/60 p-3">
                    <UserRoundIcon className="size-5 shrink-0 text-brand" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold">{h.name}</span>
                      <span className="text-xs text-muted-foreground">{t('share.since', { date: formatDate(h.added_at) })}</span>
                    </span>
                    <Button size="sm" variant="outline" loading={remove.isPending && remove.variables === h.uid} onClick={() => remove.mutate(h.uid)}>
                      {t('share.remove')}
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">{t('share.none')}</p>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{t('share.note')}</p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
