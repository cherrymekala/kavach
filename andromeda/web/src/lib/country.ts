export type CountryCode = 'IN' | 'SG'

/** Guess the country pack from a Firebase phone number; defaults to IN. */
export function countryFromPhone(phone: string | null | undefined): CountryCode {
  if (!phone) return 'IN'
  if (phone.startsWith('+65')) return 'SG'
  return 'IN'
}