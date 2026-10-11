import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MapPinIcon, MessageCircleIcon, PhoneIcon } from 'lucide-react'
import { AppHeader, Badge, FooterCTA, LanguageSwitcher } from '@/components'
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

      <div className="grid items-start gap-8 lg:grid-cols-2 lg:gap-12">
        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-2">
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPinIcon className="size-4" aria-hidden />
              {pack.name}
              {user?.phoneNumber ? ` · ${t('start.detected')}` : ''}
            </span>
            <h2 className="font-display text-2xl font-extrabold leading-tight text-balance">{t('start.hero')}</h2>
            <p className="text-muted-foreground">{t('start.heroSub')}</p>
          </section>

          <section className="flex flex-col gap-2">
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
          </section>
        </div>

        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-2">
            <h3 className="font-display text-base font-bold">{t('start.country')}</h3>
            <CountryPicker countries={COUNTRIES} value={country} onChange={chooseCountry} />
            <p className="text-xs text-muted-foreground">{t('start.countryNote')}</p>
          </section>

          <section className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3">
            <h3 className="font-display text-base font-bold">{t('auth.language')}</h3>
            <LanguageSwitcher languages={languages} />
          </section>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <p className="text-center text-xs text-muted-foreground">{t('auth.privacy')}</p>
        </div>
      </div>

      <FooterCTA
        primary={{ label: t('start.cta'), onClick: handleStart, loading: createCase.isPending }}
      />
    </div>
  )
}