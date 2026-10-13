export type CountryCode = 'IN' | 'SG'

export const COUNTRIES: { code: CountryCode; name: string }[] = [
  { code: 'IN', name: 'India' },
  { code: 'SG', name: 'Singapore' },
]

/** Guess the country pack from a Firebase phone number; defaults to IN. */
export function countryFromPhone(phone: string | null | undefined): CountryCode {
  if (!phone) return 'IN'
  if (phone.startsWith('+65')) return 'SG'
  return 'IN'
}