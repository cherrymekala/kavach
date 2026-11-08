import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Input, KavachMark, Label } from '@/components'
import { useRedeemShare } from '@/api/hooks'

/**
 * Helper mode, helper side: join a patient's case with the code they shared (/join or
 * /join/<code> from their link). The name is how the patient will see who is helping.
 */
export function JoinCase() {
  const { code: fromLink } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const redeem = useRedeemShare()
  const [code, setCode] = useState(fromLink ?? '')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function join(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const c = await redeem.mutateAsync({ code, name })
      navigate(`/case/${c.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('share.joinError'))
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-page px-5 py-10">
      <form onSubmit={join} className="flex w-full max-w-md flex-col gap-5 rounded-[28px] bg-card p-6 shadow-[0_18px_40px_rgb(46_31_184/0.08)]">
        <KavachMark className="h-9 text-ink" />
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-2xl font-bold tracking-[-0.03em]">{t('share.joinTitle')}</h1>
          <p className="text-sm text-muted-foreground">{t('share.joinSub')}</p>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="join-code">{t('share.codeLabel')}</Label>
          <Input
            id="join-code"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="ABCD-2345"
            autoComplete="off"
            className="font-display text-lg tracking-[0.08em]"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="join-name">{t('share.yourName')}</Label>
          <Input id="join-name" value={name} onChange={(e) => setName(e.target.value)} placeholder={t('share.namePlaceholder')} />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" size="lg" loading={redeem.isPending} disabled={!code.trim() || !name.trim()}>
          {t('share.join')}
        </Button>
        <p className="text-xs text-muted-foreground">{t('share.joinNote')}</p>
      </form>
    </div>
  )
}
