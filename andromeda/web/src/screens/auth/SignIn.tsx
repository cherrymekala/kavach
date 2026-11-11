import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConfirmationResult } from 'firebase/auth'
import { RecaptchaVerifier } from 'firebase/auth'
import { FileTextIcon, LanguagesIcon, SendIcon } from 'lucide-react'
import { KavachMark, KavachPlates, LanguageSwitcher, PhoneOTPForm } from '@/components'
import { auth, mapAuthError, sendOtp } from '@/firebase'
import { useAuth } from '@/auth'

const FEATURES = [
  { icon: FileTextIcon, key: 'auth.featureRead' },
  { icon: LanguagesIcon, key: 'auth.featureExplain' },
  { icon: SendIcon, key: 'auth.featureFile' },
] as const

export function SignIn() {
  const location = useLocation()
  // Back to where sign-in interrupted (e.g. a helper's /join/<code> link). Internal paths only.
  const from = (location.state as { from?: string } | null)?.from
  const next = from && from.startsWith('/') && !from.startsWith('//') ? from : '/app'
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
      navigate(next)
    } catch (e) {
      throw new Error(mapAuthError(e))
    }
  }

  if (loading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  if (user) {
    return <Navigate to={next} replace />
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-2">
      {/* Brand panel — desktop only: the plates assemble beside the headline */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-card px-12 py-12 lg:flex">
        <div className="flex items-center gap-2.5">
          <KavachMark className="h-8 text-ink" />
          <span className="font-display text-xl font-extrabold tracking-[-0.05em]">kavach</span>
        </div>

        <div className="flex items-center gap-10">
          <div className="max-w-md">
            <p className="text-sm font-semibold text-brand">{t('auth.kicker')}</p>
            <h1 className="mt-4 font-display text-[2.6rem] leading-[1.1] font-bold tracking-[-0.03em] text-balance">{t('auth.headline')}</h1>
            <p className="mt-4 text-lg text-muted-foreground">{t('auth.subhead')}</p>

            <ul className="mt-10 flex flex-col gap-4">
              {FEATURES.map(({ icon: Icon, key }) => (
                <li key={key} className="flex items-center gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground">
                    <Icon className="size-4" aria-hidden />
                  </span>
                  <span>{t(key)}</span>
                </li>
              ))}
            </ul>
          </div>
          <KavachPlates size={240} className="hidden xl:block" />
        </div>

        <p className="text-xs text-muted-foreground">
          {t('auth.privacy')}{' '}
          <a href="/guides" className="font-semibold text-brand underline">{t('guides.link')}</a>
        </p>
      </div>

      {/* Form panel */}
      <div className="flex min-h-dvh flex-col bg-page">
        <header className="flex items-center justify-between px-5 py-4 sm:px-8">
          <div className="flex items-center gap-2 lg:hidden">
            <KavachMark className="h-7 text-ink" />
            <span className="font-display text-lg font-extrabold tracking-[-0.05em]">kavach</span>
          </div>
          <LanguageSwitcher />
        </header>

        <main className="flex flex-1 items-center justify-center px-5 pb-10 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8 flex flex-col items-center text-center lg:hidden">
              <KavachPlates size={150} />
              <h1 className="mt-4 font-display text-[1.65rem] leading-[1.15] font-bold tracking-[-0.03em] text-balance">{t('auth.headline')}</h1>
              <p className="mt-3 max-w-[36ch] text-muted-foreground">{t('auth.subhead')}</p>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[0_18px_40px_rgb(46_31_184/0.08)] sm:p-8">
              <h2 className="text-xl font-extrabold tracking-tight">{t('auth.signIn')}</h2>
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
            <a href="/guides" className="mt-6 inline-block text-sm font-semibold text-brand underline">{t('guides.link')}</a>
          </div>
        </main>

        <div id="recaptcha-container" />
      </div>
    </div>
  )
}