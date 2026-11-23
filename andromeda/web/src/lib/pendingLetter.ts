/**
 * The letter a signed-out visitor checked on /check, kept in memory (never in storage) so
 * that after phone sign-in, which happens in the same page, it becomes their first case
 * without uploading it again. A reload loses it, which is fine: they just pick the file again.
 */
export type PendingLetter = { file: File; country: string }

let pending: PendingLetter | null = null

export function keepLetter(letter: PendingLetter) {
  pending = letter
}

export function takeLetter(): PendingLetter | null {
  const p = pending
  pending = null
  return p
}

type Fetch = <T>(path: string, init?: RequestInit) => Promise<T>

/** Create the case, upload the checked letter and start the analysis. Returns the case id. */
export async function startCaseFromLetter(letter: PendingLetter, language: string, api: Fetch): Promise<string> {
  const kase = await api<{ id: string }>('/cases', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ country: letter.country, language, kind: 'dispute' }),
  })
  const form = new FormData()
  form.append('file', letter.file)
  await api(`/cases/${kase.id}/documents`, { method: 'POST', body: form })
  await api(`/cases/${kase.id}/analyse`, { method: 'POST' })
  return kase.id
}
