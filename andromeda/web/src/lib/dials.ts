import { getCountries, getCountryCallingCode } from 'libphonenumber-js'

export interface CountryDial {
  code: string
  dial: string
  name: string
  flag: string
  label: string
}

const regionNames = new Intl.DisplayNames(['en'], { type: 'region' })

function flagEmoji(iso: string): string {
  return iso
    .toUpperCase()
    .replace(/./g, (c) => String.fromCodePoint(0x1f1e6 + c.charCodeAt(0) - 65))
}

function nameFor(iso: string): string {
  try {
    return regionNames.of(iso) ?? iso
  } catch {
    return iso
  }
}

const PREFERRED = ['IN', 'SG']

function buildDials(): CountryDial[] {
  return getCountries()
    .map((code) => {
      const dial = `+${getCountryCallingCode(code)}`
      const name = nameFor(code)
      const flag = flagEmoji(code)
      return { code, dial, name, flag, label: `${flag} ${dial} ${name}` }
    })
    .sort((a, b) => {
      const pa = PREFERRED.indexOf(a.code)
      const pb = PREFERRED.indexOf(b.code)
      if (pa !== -1 || pb !== -1) {
        if (pa === -1) return 1
        if (pb === -1) return -1
        return pa - pb
      }
      return a.name.localeCompare(b.name)
    })
}

/** Every country dial code, with India and Singapore first, then the rest A→Z. */
export const ALL_DIALS: CountryDial[] = buildDials()