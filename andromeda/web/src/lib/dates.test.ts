import { describe, expect, it } from 'vitest'
import { formatDeadline } from './dates'

describe('formatDeadline', () => {
  it('shows the calendar day the backend set, whatever the viewer time zone', () => {
    // 23:59 UTC on 21 Nov is already 22 Nov in India; the deadline is still the 21st.
    expect(formatDeadline('2026-11-21T23:59:00Z')).toContain('21')
  })
})
