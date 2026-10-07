import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ConfirmationResult } from 'firebase/auth'
import { RecaptchaVerifier } from 'firebase/auth'
import { LanguagePicker, PhoneOTPForm, ThemeToggle } from '@/components'
import { auth, mapAuthError, sendOtp } from '@/firebase'
import { useAuth } from '@/auth'

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'mr', label: 'मराठी' },
  { code: 'zh', label: '中文' },
]

const LANGUAGE_KEY = 'kavach-language'

export function SignIn() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const [language, setLanguage] = useState(() => window.localStorage.getItem(LANGUAGE_KEY) ?? 'en')
  const [confirmation, setConfirmation] = useState<ConfirmationResult | null>(null)
  const verifierRef = useRef<RecaptchaVerifier | null>(null)

  function chooseLanguage(code: string) {
    setLanguage(code)
    window.localStorage.setItem(LANGUAGE_KEY, code)
  }

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
    return <div className="py-16 text-center text-sm text-muted-foreground">Loading…</div>
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end">
        <ThemeToggle />
      </div>

      <section className="flex flex-col gap-3 rounded-2xl bg-primary p-6 text-primary-foreground">
        <span className="font-mono text-xs opacity-80">Health insurance, defended</span>
        <h1 className="font-display text-2xl font-extrabold leading-tight text-balance">
          Claim rejected? Let's fight it together.
        </h1>
        <p className="text-sm opacity-85">
          We read your documents, explain the rejection in your language, and file the appeal for you.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Language</h2>
        <LanguagePicker languages={LANGUAGES} value={language} onChange={chooseLanguage} />
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Sign in</h2>
        <PhoneOTPForm onSend={handleSend} onVerify={handleVerify} />
        <p className="text-center text-xs text-muted-foreground">
          {user ? `Signed in as ${user.phoneNumber ?? 'you'}.` : 'A one-time code is sent to your phone. We never share your documents.'}
        </p>
      </section>

      <div id="recaptcha-container" />
    </div>
  )
}