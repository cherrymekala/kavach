import { useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConfirmationResult } from 'firebase/auth'
import { RecaptchaVerifier } from 'firebase/auth'
import { FileTextIcon, LanguagesIcon, SendIcon, ShieldCheckIcon } from 'lucide-react'
import { LanguageSwitcher, PhoneOTPForm } from '@/components'
import { auth, mapAuthError, sendOtp } from '@/firebase'
import { useAuth } from '@/auth'

const FEATURES = [
  { icon: FileTextIcon, key: 'auth.featureRead' },
  { icon: LanguagesIcon, key: 'auth.featureExplain' },
  { icon: SendIcon, key: 'auth.featureFile' },
] as const

export function SignIn() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { user, loading } = useAuth()
  const [confirmation, setConfirmation] = useState<ConfirmationResult | null>(null)
  const verifierRef = useRef<RecaptchaVerifier | null>(null)

  async function handleSend(phone: string) {
    try {
      verifierRef.current?.clear()
      const verifier = new RecaptchaVerifier(auth(), 'recaptcha-container', { size: 'invisible' })
      verifierRef.current = verifier
      setConfirmation(await sendOtp(phone, verifier))
    } catch (e) {
      throw new Error(mapAuthError(e))
    }
  }

  async function handleVerify(code: string) {
    if (!confirmation) throw new Error('Verification not started. Send a new code.')
    try {
      await confirmation.confirm(code)
      verifierRef.current?.clear()
      navigate('/app')
    } catch (e) {
      throw new Error(mapAuthError(e))
    }
  }

  if (loading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  if (user) {
    return <Navigate to="/app" replace />
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-2">
      {/* Evergreen brand panel — desktop only */}
      <div className="hidden flex-col justify-between bg-brand px-12 py-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-lg bg-white/10">
            <ShieldCheckIcon className="size-5" aria-hidden />
          </span>
          <span className="font-display text-lg font-bold tracking-tight">Kavach</span>
        </div>

        <div className="max-w-md">
          <p className="font-mono text-xs font-bold uppercase tracking-widest text-white/60">{t('auth.kicker')}</p>
          <h1 className="mt-4 font-display text-4xl font-extrabold leading-tight text-balance">{t('auth.headline')}</h1>
          <p className="mt-4 text-lg text-white/70">{t('auth.subhead')}</p>

          <ul className="mt-10 flex flex-col gap-4">
            {FEATURES.map(({ icon: Icon, key }) => (
              <li key={key} className="flex items-center gap-3">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-white/10">
                  <Icon className="size-4" aria-hidden />
                </span>
                <span className="text-white/90">{t(key)}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-white/50">{t('auth.privacy')}</p>
      </div>

      {/* Form panel */}
      <div className="flex min-h-dvh flex-col bg-page">
        <header className="flex items-center justify-between px-5 py-4 sm:px-8">
          <div className="flex items-center gap-2.5 lg:hidden">
            <span className="grid size-8 place-items-center rounded-lg bg-brand text-white">
              <ShieldCheckIcon className="size-5" aria-hidden />
            </span>
            <span className="font-display text-lg font-bold tracking-tight">Kavach</span>
          </div>
          <LanguageSwitcher />
        </header>

        <main className="flex flex-1 items-center justify-center px-5 pb-10 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-6 lg:hidden">
              <p className="font-mono text-xs font-bold uppercase tracking-widest text-brand">{t('auth.kicker')}</p>
              <h1 className="mt-3 font-display text-3xl font-extrabold leading-tight text-balance">{t('auth.headline')}</h1>
              <p className="mt-3 text-muted-foreground">{t('auth.subhead')}</p>
            </div>

            <div className="rounded-2xl border border-line bg-card p-6 shadow-sm sm:p-8">
              <h2 className="font-display text-lg font-bold">{t('auth.signIn')}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t('auth.privacy')}</p>
              <div className="mt-5">
                <PhoneOTPForm onSend={handleSend} onVerify={handleVerify} />
              </div>
            </div>

            <ul className="mt-6 flex flex-col gap-2.5 lg:hidden">
              {FEATURES.map(({ icon: Icon, key }) => (
                <li key={key} className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-soft text-brand">
                    <Icon className="size-4" aria-hidden />
                  </span>
                  {t(key)}
                </li>
              ))}
            </ul>
          </div>
        </main>

        <div id="recaptcha-container" />
      </div>
    </div>
  )
}