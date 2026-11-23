import { apiFetch } from './client'
import type { components } from './schema'

export type PreviewResult = components['schemas']['PreviewResult']

/** Public, rate-limited, nothing stored (sombrero/src/kavach/routers/preview.py). */
export function previewLetter(file: File, country: string): Promise<PreviewResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('country', country)
  return apiFetch<PreviewResult>('/preview', { method: 'POST', body: form })
}
