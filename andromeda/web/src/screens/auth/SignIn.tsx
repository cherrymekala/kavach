import { useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConfirmationResult } from 'firebase/auth'
import { RecaptchaVerifier } from 'firebase/auth'
import { FileTextIcon, LanguagesIcon, SendIcon } from 'lucide-react'
import { LanguageSwitcher, PhoneOTPForm, ThemeToggle } from '@/components'
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
      navigate('/start')
    } catch (e) {
      throw new Error(mapAuthError(e))
    }
  }

  if (loading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">{t('common.loading')}</div>
  }

  if (user) {
    return <Navigate to="/start" replace />
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end">
        <ThemeToggle />
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-2 lg:gap-12">
        <section className="flex flex-col gap-4 rounded-3xl bg-primary p-6 text-primary-foreground sm:p-8 lg:p-10">
          <span className="font-mono text-xs uppercase tracking-wider opacity-80">{t('auth.kicker')}</span>
          <h1 className="font-display text-2xl font-extrabold leading-tight text-balance sm:text-3xl lg:text-4xl">
            {t('auth.headline')}
          </h1>
          <p className="text-sm opacity-90 sm:text-base">{t('auth.subhead')}</p>

          <ul className="mt-2 hidden flex-col gap-3 sm:flex">
            {FEATURES.map(({ icon: Icon, key }) => (
              <li key={key} className="flex items-center gap-3 text-sm sm:text-base">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-white/10">
                  <Icon className="size-4" aria-hidden />
                </span>
                {t(key)}
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-6 lg:pt-2">
          <section className="flex flex-col gap-2">
            <h2 className="font-display text-lg font-bold">{t('auth.language')}</h2>
            <LanguageSwitcher />
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="font-display text-lg font-bold">{t('auth.signIn')}</h2>
            <PhoneOTPForm onSend={handleSend} onVerify={handleVerify} />
            <p className="text-center text-xs text-muted-foreground">{t('auth.privacy')}</p>
          </section>
        </section>
      </div>

      <div id="recaptcha-container" />
    </div>
  )
}