import { describe, expect, it } from 'vitest'
import { keepLetter, startCaseFromLetter, takeLetter } from './pendingLetter'

describe('pending letter', () => {
  it('is handed over once, then gone', () => {
    const file = new File(['letter'], 'letter.pdf', { type: 'application/pdf' })
    keepLetter({ file, country: 'SG' })
    expect(takeLetter()?.country).toBe('SG')
    expect(takeLetter()).toBeNull()
  })

  it('creates the case in the right country, uploads the same file, then analyses', async () => {
    const file = new File(['letter'], 'letter.pdf', { type: 'application/pdf' })
    const calls: { path: string; init?: RequestInit }[] = []
    const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
      calls.push({ path, init })
      return (path === '/cases' ? { id: 'c1' } : {}) as T
    }
    expect(await startCaseFromLetter({ file, country: 'MY' }, 'ms', api)).toBe('c1')
    expect(calls.map((c) => c.path)).toEqual(['/cases', '/cases/c1/documents', '/cases/c1/analyse'])
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ country: 'MY', language: 'ms', kind: 'dispute' })
    expect((calls[1].init?.body as FormData).get('file')).toBe(file)
  })
})
