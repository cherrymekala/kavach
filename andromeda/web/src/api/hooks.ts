import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type {
  Case,
  Complainant,
  CreateCase,
  Document,
  FiledRequest,
  FilingPack,
  Letter,
  LetterRequest,
  ReplyRequest,
} from './types'

export function caseKey(id?: string): unknown[] {
  return ['case', id]
}

function jsonBody(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

// ── Cases ────────────────────────────────────────────────────────────────

export function useCreateCase() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateCase) => apiFetch<Case>('/cases', jsonBody(body)),
    onSuccess: (c) => qc.setQueryData(caseKey(c.id), c),
  })
}

export function useCase(id: string | undefined) {
  return useQuery({
    queryKey: caseKey(id),
    queryFn: () => apiFetch<Case>(`/cases/${id}`),
    enabled: Boolean(id),
  })
}

export function useDeleteCase() {
  return useMutation({ mutationFn: (id: string) => apiFetch<void>(`/cases/${id}`, { method: 'DELETE' }) })
}

// ── Documents & analysis ─────────────────────────────────────────────────

export function useUploadDocument(caseId: string) {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return apiFetch<Document>(`/cases/${caseId}/documents`, { method: 'POST', body: form })
    },
  })
}

export function useAnalyse(caseId: string) {
  return useMutation({
    mutationFn: () => apiFetch<Record<string, unknown>>(`/cases/${caseId}/analyse`, { method: 'POST' }),
  })
}

// ── Filing ───────────────────────────────────────────────────────────────

export function useSetComplainant(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Complainant) =>
      apiFetch<Case>(`/cases/${caseId}/complainant`, { method: 'PUT', ...jsonBody(body) }),
    onSuccess: (c) => qc.setQueryData(caseKey(caseId), c),
  })
}

export function useRedraftLetter(caseId: string) {
  return useMutation({
    mutationFn: (body: LetterRequest) => apiFetch<Letter>(`/cases/${caseId}/letter`, jsonBody(body)),
  })
}

export function useFiling(caseId: string, step?: number) {
  const query = step !== undefined ? `?step=${step}` : ''
  return useQuery({
    queryKey: ['filing', caseId, step],
    queryFn: () => apiFetch<FilingPack>(`/cases/${caseId}/filing${query}`),
    enabled: Boolean(caseId),
  })
}

// ── Tracker ──────────────────────────────────────────────────────────────

export function useMarkFiled(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: FiledRequest) => apiFetch<Case>(`/cases/${caseId}/filed`, jsonBody(body)),
    onSuccess: (c) => qc.setQueryData(caseKey(caseId), c),
  })
}

export function useRecordReply(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReplyRequest) => apiFetch<Case>(`/cases/${caseId}/reply`, jsonBody(body)),
    onSuccess: (c) => qc.setQueryData(caseKey(caseId), c),
  })
}