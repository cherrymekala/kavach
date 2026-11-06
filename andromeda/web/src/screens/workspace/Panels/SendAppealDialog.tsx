import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangleIcon, FileTextIcon, MailIcon } from 'lucide-react'
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
} from '@/components'
import { useAppealMail, useSendAppeal } from '@/api/hooks'
import type { AppealMail } from '@/api/types'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

/**
 * "Email it for me": Kavach sends the appeal letter to the insurer's grievance officer, with
 * the patient in copy and the case's own reply address, then starts the reply deadline.
 */
export function SendAppealDialog({ caseId, open, onClose }: { caseId: string; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const { data: mail, isLoading } = useAppealMail(caseId, open)
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('tracker.email.title')}</DialogTitle>
          <DialogDescription>{t('tracker.email.sub')}</DialogDescription>
        </DialogHeader>
        {isLoading || !mail ? (
          <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
        ) : (
          // Mounted once the preview is loaded, so the form starts from it (no syncing effect).
          <AppealForm caseId={caseId} mail={mail} onSent={onClose} />
        )}
      </DialogContent>
    </Dialog>
  )
}

function AppealForm({ caseId, mail, onSent }: { caseId: string; mail: AppealMail; onSent: () => void }) {
  const { t } = useTranslation()
  const send = useSendAppeal(caseId)
  const [to, setTo] = useState(mail.to ?? '')
  const [error, setError] = useState<string | null>(null)

  // "step" and "already_sent" can't be fixed from here; the rest point to what to fill in.
  const blockers = mail.missing.filter((m) => m !== 'step' && m !== 'already_sent')
  const valid = EMAIL.test(to.trim())

  async function submit() {
    setError(null)
    try {
      await send.mutateAsync(to.trim())
      onSent()
    } catch (e) {
      setError(e instanceof Error ? e.message : t('tracker.email.error'))
    }
  }

  return (
    <>
      <div className="flex flex-col gap-4">
        {blockers.length ? (
          <ul className="flex flex-col gap-2 rounded-2xl bg-[#ffe3da] p-4 text-sm text-[#5c1605] dark:bg-[#3a1f19] dark:text-[#ffd3c6]">
            {blockers.map((m) => (
              <li key={m} className="flex gap-2">
                <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" aria-hidden />
                {t(`tracker.email.missing.${m}`, { list: mail.blanks.join(', ') })}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="appeal-to">{t('tracker.email.to')}</Label>
          <Input
            id="appeal-to"
            type="email"
            inputMode="email"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="gro@insurer.com"
            aria-invalid={Boolean(to) && !valid}
          />
          {mail.to_source === 'directory' && to === mail.to ? (
            <p className="text-xs text-muted-foreground">{t('tracker.email.fromDirectory')}</p>
          ) : null}
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-2xl bg-muted/60 p-4 text-sm">
          <dt className="text-muted-foreground">{t('tracker.email.cc')}</dt>
          <dd className="min-w-0 truncate font-medium">{mail.cc ?? '—'}</dd>
          <dt className="text-muted-foreground">{t('tracker.email.attachments')}</dt>
          <dd className="flex min-w-0 flex-col gap-1">
            {mail.attachments.map((a) => (
              <span key={a} className="flex items-center gap-1.5 font-medium">
                <FileTextIcon className="size-3.5 shrink-0 text-brand" aria-hidden />
                <span className="truncate">{a}</span>
              </span>
            ))}
          </dd>
        </dl>

        {mail.dry_run ? <p className="text-xs text-muted-foreground">{t('tracker.email.testMode')}</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </div>

      <DialogFooter>
        <Button onClick={submit} loading={send.isPending} disabled={blockers.length > 0 || !valid}>
          <MailIcon aria-hidden />
          {t('tracker.email.send')}
        </Button>
      </DialogFooter>
    </>
  )
}
