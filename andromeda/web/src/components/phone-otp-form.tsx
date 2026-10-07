import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export interface CountryDial {
  code: string
  dial: string
  label: string
}

export interface PhoneOTPFormProps {
  dials?: CountryDial[]
  /** Resolve when the code is sent; reject with an Error to show its message. */
  onSend: (fullPhone: string) => Promise<void>
  /** Resolve on success; reject with an Error to show its message. */
  onVerify: (code: string) => Promise<void>
}

export const DEFAULT_DIALS: CountryDial[] = [
  { code: 'IN', dial: '+91', label: '🇮🇳 +91' },
  { code: 'SG', dial: '+65', label: '🇸🇬 +65' },
]

export function PhoneOTPForm({ dials = DEFAULT_DIALS, onSend, onVerify }: PhoneOTPFormProps) {
  const [dial, setDial] = useState(dials[0]?.dial ?? '')
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
      setError(e instanceof Error ? e.message : 'Could not send the code.')
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
      setError(e instanceof Error ? e.message : 'Could not verify the code.')
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
          <Label>Enter the 6-digit code</Label>
          <InputOTP maxLength={6} value={code} onChange={setCode}>
            <InputOTPGroup>
              {Array.from({ length: 6 }).map((_, i) => (
                <InputOTPSlot key={i} index={i} />
              ))}
            </InputOTPGroup>
          </InputOTP>
          <p className="text-xs text-muted-foreground">
            Sent to {dial} {phone}.{' '}
            <button type="button" onClick={() => setStage('phone')} className="text-brand underline">
              Change number
            </button>
          </p>
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" loading={busy} disabled={code.length < 6}>
          Verify code
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
        <Label htmlFor="phone">Phone number</Label>
        <div className="flex gap-2">
          <Select value={dial} onValueChange={setDial}>
            <SelectTrigger className="w-[104px] shrink-0" aria-label="Country dial code">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {dials.map((d) => (
                <SelectItem key={d.dial} value={d.dial}>
                  {d.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            id="phone"
            type="tel"
            inputMode="numeric"
            placeholder="99999 00001"
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
            className="flex-1"
            autoComplete="tel"
          />
        </div>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" loading={busy} disabled={phone.length < 6}>
        Send code
      </Button>
    </form>
  )
}