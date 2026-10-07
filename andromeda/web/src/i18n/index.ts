import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import hi from './hi.json'
import ta from './ta.json'
import te from './te.json'
import mr from './mr.json'
import zh from './zh.json'
import ms from './ms.json'

export const LANGUAGE_KEY = 'kavach-language'

export const SUPPORTED_LANGUAGES: { code: string; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'mr', label: 'मराठी' },
  { code: 'zh', label: '中文' },
  { code: 'ms', label: 'Bahasa Melayu' },
]

/**
 * No auto-detection: the app always starts in English (or the user's last
 * explicit choice). Language only changes when the user taps a button.
 */
function initialLanguage(): string {
  const stored = window.localStorage.getItem(LANGUAGE_KEY)
  return stored && SUPPORTED_LANGUAGES.some((l) => l.code === stored) ? stored : 'en'
}

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  ta: { translation: ta },
  te: { translation: te },
  mr: { translation: mr },
  zh: { translation: zh },
  ms: { translation: ms },
}

i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage(),
  fallbackLng: 'en',
  supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (lng) => {
  window.localStorage.setItem(LANGUAGE_KEY, lng)
  document.documentElement.lang = lng
})

document.documentElement.lang = i18n.language

export default i18n