import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'
import { Label } from '@/components/ui/label'
import { CountrySelect } from './country-select'
import { ALL_DIALS } from '@/lib/dials'

export interface PhoneOTPFormProps {
  /** Resolve when the code is sent; reject with an Error to show its message. */
  onSend: (fullPhone: string) => Promise<void>
  /** Resolve on success; reject with an Error to show its message. */
  onVerify: (code: string) => Promise<void>
}

export function PhoneOTPForm({ onSend, onVerify }: PhoneOTPFormProps) {
  const { t } = useTranslation()
  const [dial, setDial] = useState(ALL_DIALS[0]?.dial ?? '+91')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [stage, setStage] = useState<'phone' | 'otp'>('phone')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSend() {
    setError(null)
    setBusy(true)
    try {
      await onSend(`${dial}${phone}`)
      setStage('otp')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('otp.errorSend'))
    } finally {
      setBusy(false)
    }
  }

  async function handleVerify() {
    setError(null)
    setBusy(true)
    try {
      await onVerify(code)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('otp.errorVerify'))
    } finally {
      setBusy(false)
    }
  }

  if (stage === 'otp') {
    return (
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          handleVerify()
        }}
      >
        <div className="flex flex-col gap-2">
          <Label>{t('otp.codeLabel')}</Label>
          <InputOTP maxLength={6} value={code} onChange={setCode}>
            <InputOTPGroup>
              {Array.from({ length: 6 }).map((_, i) => (
                <InputOTPSlot key={i} index={i} />
              ))}
            </InputOTPGroup>
          </InputOTP>
          <p className="text-xs text-muted-foreground">
            {t('otp.sentTo', { dial, phone })}{' '}
            <button type="button" onClick={() => setStage('phone')} className="text-brand underline">
              {t('otp.changeNumber')}
            </button>
          </p>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" loading={busy} disabled={code.length < 6}>
          {t('otp.verifyCode')}
        </Button>
      </form>
    )
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        handleSend()
      }}
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="phone">{t('otp.phoneLabel')}</Label>
        <div className="flex gap-2">
          <CountrySelect value={dial} onChange={setDial} />
          <Input
            id="phone"
            type="tel"
            inputMode="numeric"
            placeholder={t('otp.phonePlaceholder')}
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
            className="flex-1"
            autoComplete="tel"
          />
        </div>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" loading={busy} disabled={phone.length < 6}>
        {t('otp.sendCode')}
      </Button>
    </form>
  )
}