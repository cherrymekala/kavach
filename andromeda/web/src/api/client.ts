import { getIdToken } from '../firebase'

const API_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function authHeaders(): Promise<Headers> {
  const headers = new Headers()
  const token = await getIdToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return headers
}

/**
 * Fetch JSON from the Kavach API. Errors arrive as `{"detail": "..."}` with a
 * user-friendly message — throw it as ApiError so the UI can show it verbatim.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = await authHeaders()
  for (const [k, v] of new Headers(init.headers).entries()) headers.set(k, v)
  const res = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res))
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** Fetch a binary (PDF) with auth — needed because PDF endpoints can't be a plain <a href>. */
export async function apiBlob(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, { headers: await authHeaders() })
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res))
  return res.blob()
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? '').filter(Boolean).join(' ')
    return res.statusText
  } catch {
    return res.statusText
  }
}