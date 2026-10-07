import { useTranslation } from 'react-i18next'
import { LanguagePicker } from './language-picker'
import { SUPPORTED_LANGUAGES } from '@/i18n'

/** Button-driven language switcher — changes language only on explicit tap. */
export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  return (
    <LanguagePicker
      languages={SUPPORTED_LANGUAGES}
      value={i18n.resolvedLanguage ?? 'en'}
      onChange={(code) => i18n.changeLanguage(code)}
    />
  )
}