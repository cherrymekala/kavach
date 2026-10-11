export type CountryCode = 'IN' | 'SG'

export interface CountryOption {
  code: CountryCode
  flag: string
  name: string
  languages: string[]
  regulator: string
  currency: string
}

export const COUNTRIES: CountryOption[] = [
  { code: 'IN', flag: '🇮🇳', name: 'India', languages: ['en', 'hi', 'ta', 'te', 'mr'], regulator: 'IRDAI', currency: 'INR' },
  { code: 'SG', flag: '🇸🇬', name: 'Singapore', languages: ['en', 'zh', 'ms', 'ta'], regulator: 'MAS', currency: 'SGD' },
]

export function countryFromPhone(phone: string | null | undefined): CountryCode | null {
  if (!phone) return null
  if (phone.startsWith('+91')) return 'IN'
  if (phone.startsWith('+65')) return 'SG'
  return null
}