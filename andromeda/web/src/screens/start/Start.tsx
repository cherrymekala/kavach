import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MapPinIcon, MessageCircleIcon, PhoneIcon } from 'lucide-react'
import { AppHeader, Badge, Button, LanguagePicker } from '@/components'
import { SUPPORTED_LANGUAGES } from '@/i18n'
import { useCreateCase } from '@/api/hooks'
import { useAuth } from '@/auth'
import { COUNTRIES, countryFromPhone, type CountryCode } from './countries'
import { CountryPicker } from './CountryPicker'

export function Start() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const createCase = useCreateCase()
  const [country, setCountry] = useState<CountryCode>(countryFromPhone(user?.phoneNumber) ?? 'IN')
  const [error, setError] = useState<string | null>(null)

  const pack = COUNTRIES.find((c) => c.code === country) ?? COUNTRIES[0]
  const languages = SUPPORTED_LANGUAGES.filter((l) => pack.languages.includes(l.code))

  function chooseCountry(code: CountryCode) {
    setCountry(code)
    const next = COUNTRIES.find((c) => c.code === code)
    if (next && !next.languages.includes(i18n.language)) i18n.changeLanguage('en')
  }

  async function handleStart() {
    setError(null)
    try {
      const created = await createCase.mutateAsync({ country, language: i18n.language })
      navigate(`/case/${created.id}/upload`)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('start.errorCreate'))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <AppHeader title={t('start.title')} pack={country} />

      <div className="grid items-start gap-6 lg:grid-cols-2 lg:gap-12">
        <section className="flex flex-col gap-6">
          <section className="flex flex-col gap-4 rounded-3xl bg-primary p-6 text-primary-foreground sm:p-8">
            <span className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider opacity-80">
              <MapPinIcon className="size-4" aria-hidden />
              {pack.name}
              {user?.phoneNumber ? ` · ${t('start.detected')}` : ''}
            </span>
            <h1 className="font-display text-2xl font-extrabold leading-tight text-balance sm:text-3xl">
              {t('auth.headline')}
            </h1>
            <p className="text-sm opacity-90 sm:text-base">{t('auth.subhead')}</p>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="font-display text-lg font-bold">{t('start.otherWays')}</h2>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4 text-card-foreground">
                <MessageCircleIcon className="size-5 text-muted-foreground" aria-hidden />
                <p className="mt-1 font-semibold">{t('start.whatsapp')}</p>
                <p className="text-xs text-muted-foreground">{t('start.whatsappDesc')}</p>
                <Badge variant="secondary" className="mt-1 self-start">
                  {t('start.comingSoon')}
                </Badge>
              </div>
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card p-4 text-card-foreground">
                <PhoneIcon className="size-5 text-muted-foreground" aria-hidden />
                <p className="mt-1 font-semibold">{t('start.call')}</p>
                <p className="text-xs text-muted-foreground">{t('start.callDesc')}</p>
                <Badge variant="secondary" className="mt-1 self-start">
                  {t('start.comingSoon')}
                </Badge>
              </div>
            </div>
          </section>
        </section>

        <section className="flex flex-col gap-6">
          <section className="flex flex-col gap-3">
            <h2 className="font-display text-lg font-bold">{t('start.country')}</h2>
            <CountryPicker countries={COUNTRIES} value={country} onChange={chooseCountry} />
            <p className="text-xs text-muted-foreground">{t('start.countryNote')}</p>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="font-display text-lg font-bold">{t('auth.language')}</h2>
            <LanguagePicker
              languages={languages}
              value={i18n.resolvedLanguage ?? 'en'}
              onChange={(code) => i18n.changeLanguage(code)}
            />
          </section>

          <Button size="lg" className="w-full" loading={createCase.isPending} onClick={handleStart}>
            {t('start.cta')}
          </Button>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <p className="text-center text-xs text-muted-foreground">{t('auth.privacy')}</p>
        </section>
      </div>
    </div>
  )
}