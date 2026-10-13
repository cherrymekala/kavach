import { useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ConfirmationResult } from 'firebase/auth'
import { RecaptchaVerifier } from 'firebase/auth'
import { FileTextIcon, LanguagesIcon, MessageCircleIcon, PhoneIcon, SendIcon, ShieldCheckIcon } from 'lucide-react'
import { Badge, LanguageSwitcher, PhoneOTPForm } from '@/components'
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
    <div className="flex min-h-dvh flex-col bg-page">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-brand text-white">
            <ShieldCheckIcon className="size-5" aria-hidden />
          </span>
          <span className="font-display text-lg font-bold tracking-tight">Kavach</span>
        </div>
        <LanguageSwitcher />
      </header>

      <main className="mx-auto grid w-full max-w-5xl flex-1 items-start gap-8 px-5 pb-12 sm:px-6 lg:grid-cols-2 lg:gap-12 lg:pt-6">
        <section className="flex flex-col gap-3">
          <p className="font-mono text-xs font-bold uppercase tracking-widest text-brand">{t('auth.kicker')}</p>
          <h1 className="font-display text-3xl font-extrabold leading-tight text-balance sm:text-4xl">{t('auth.headline')}</h1>
          <p className="max-w-lg text-muted-foreground sm:text-lg">{t('auth.subhead')}</p>

          <ul className="mt-2 flex flex-col gap-2.5">
            {FEATURES.map(({ icon: Icon, key }) => (
              <li key={key} className="flex items-center gap-3 text-sm">
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground">
                  <Icon className="size-4" aria-hidden />
                </span>
                {t(key)}
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-4">
          <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-xs sm:p-6">
            <h2 className="font-display text-lg font-bold">{t('auth.signIn')}</h2>
            <PhoneOTPForm onSend={handleSend} onVerify={handleVerify} />
            <p className="text-center text-xs text-muted-foreground">{t('auth.privacy')}</p>
          </div>

          <div className="flex flex-col gap-2">
            <h3 className="font-display text-base font-bold">{t('start.otherWays')}</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4">
                <MessageCircleIcon className="size-5 text-muted-foreground" aria-hidden />
                <p className="mt-2 font-semibold">{t('start.whatsapp')}</p>
                <p className="text-xs text-muted-foreground">{t('start.whatsappDesc')}</p>
                <Badge variant="secondary" className="mt-2 self-start">
                  {t('start.comingSoon')}
                </Badge>
              </div>
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4">
                <PhoneIcon className="size-5 text-muted-foreground" aria-hidden />
                <p className="mt-2 font-semibold">{t('start.call')}</p>
                <p className="text-xs text-muted-foreground">{t('start.callDesc')}</p>
                <Badge variant="secondary" className="mt-2 self-start">
                  {t('start.comingSoon')}
                </Badge>
              </div>
            </div>
          </div>
        </section>
      </main>

      <div id="recaptcha-container" />
    </div>
  )
}