export type CountryCode = 'IN' | 'SG' | 'MY'

export const COUNTRIES: { code: CountryCode; name: string }[] = [
  { code: 'IN', name: 'India' },
  { code: 'SG', name: 'Singapore' },
  { code: 'MY', name: 'Malaysia' },
]

/** Guess the country pack from a Firebase phone number; defaults to IN. */
export function countryFromPhone(phone: string | null | undefined): CountryCode {
  if (!phone) return 'IN'
  if (phone.startsWith('+65')) return 'SG'
  if (phone.startsWith('+60')) return 'MY'
  return 'IN'
}

/** Fallback currency when the documents don't state one. */
export function currencyFor(country: string | null | undefined): string {
  return { SG: 'SGD', MY: 'MYR' }[country ?? ''] ?? 'INR'
}
