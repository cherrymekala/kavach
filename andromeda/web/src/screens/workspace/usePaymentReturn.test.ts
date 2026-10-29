import { describe, expect, it } from 'vitest'
import { hasPaidFlag, withoutPaidFlag } from './usePaymentReturn'

describe('hasPaidFlag', () => {
  it('recognises what Stripe sends us back with', () => {
    expect(hasPaidFlag('?paid=1')).toBe(true)
    expect(hasPaidFlag('?ref=x&paid=1')).toBe(true)
  })

  it('ignores anything else', () => {
    expect(hasPaidFlag('')).toBe(false)
    expect(hasPaidFlag('?paid=0')).toBe(false)
    expect(hasPaidFlag('?paid=true')).toBe(false)
    expect(hasPaidFlag('?unpaid=1')).toBe(false)
  })
})

describe('withoutPaidFlag', () => {
  it('drops the flag but keeps the rest of the URL', () => {
    expect(withoutPaidFlag('/case/c1', '?paid=1', '')).toBe('/case/c1')
    expect(withoutPaidFlag('/case/c1', '?paid=1&tab=letter', '')).toBe('/case/c1?tab=letter')
    expect(withoutPaidFlag('/case/c1', '?tab=letter&paid=1', '#filing')).toBe(
      '/case/c1?tab=letter#filing',
    )
  })

  it('leaves a URL with no flag alone', () => {
    expect(withoutPaidFlag('/case/c1', '?tab=letter', '')).toBe('/case/c1?tab=letter')
    expect(withoutPaidFlag('/case/c1', '', '')).toBe('/case/c1')
  })
})
