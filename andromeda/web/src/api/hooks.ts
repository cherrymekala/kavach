import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type {
  AskAnswer,
  AskRequest,
  Case,
  CaseSummary,
  Complainant,
  CreateCase,
  Document,
  FiledRequest,
  FilingPack,
  Insights,
  Letter,
  LetterRequest,
  NoteRequest,
  PackInfo,
  ReplyRequest,
  TitleRequest,
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

export function useCases() {
  return useQuery({ queryKey: ['cases'], queryFn: () => apiFetch<CaseSummary[]>('/cases') })
}

export function useCase(id: string | undefined) {
  return useQuery({
    queryKey: caseKey(id),
    queryFn: () => apiFetch<Case>(`/cases/${id}`),
    enabled: Boolean(id),
    // Local dev has no Firestore, so poll while the pipeline runs.
    refetchInterval: (query) => (query.state.data?.status === 'analysing' ? 1500 : false),
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

export function useDeleteDocument(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (docId: string) =>
      apiFetch<void>(`/cases/${caseId}/documents/${docId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: caseKey(caseId) }),
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
      apiFetch<Case>(`/cases/${caseId}/complainant`, { ...jsonBody(body), method: 'PUT' }),
    onSuccess: (c) => qc.setQueryData(caseKey(caseId), c),
  })
}

export function useRedraftLetter(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LetterRequest) => apiFetch<Letter>(`/cases/${caseId}/letter`, jsonBody(body)),
    onSuccess: (letter) => qc.setQueryData<Case>(caseKey(caseId), (c) => (c ? { ...c, letter } : c)),
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

// ── Packs ─────────────────────────────────────────────────────────────────

export function usePack(country: string | undefined) {
  return useQuery({
    queryKey: ['pack', country],
    queryFn: () => apiFetch<PackInfo>(`/packs/${country}`),
    enabled: Boolean(country),
    staleTime: Infinity,
  })
}

// ── Case title, notes & questions ─────────────────────────────────────────

export function useSetTitle(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TitleRequest) =>
      apiFetch<Case>(`/cases/${caseId}/title`, { ...jsonBody(body), method: 'PUT' }),
    onSuccess: (c) => {
      qc.setQueryData(caseKey(caseId), c)
      qc.invalidateQueries({ queryKey: ['cases'] })
    },
  })
}

export function useAddNote(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: NoteRequest) => apiFetch<Case>(`/cases/${caseId}/notes`, jsonBody(body)),
    onSuccess: (c) => qc.setQueryData(caseKey(caseId), c),
  })
}

export function useAsk(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AskRequest) => apiFetch<AskAnswer>(`/cases/${caseId}/ask`, jsonBody(body)),
    onSuccess: () => qc.invalidateQueries({ queryKey: caseKey(caseId) }),
  })
}

export function useInsights(country: string) {
  return useQuery({
    queryKey: ['insights', country],
    queryFn: () => apiFetch<Insights>(`/insights/${country}`),
    staleTime: Infinity,
    retry: false,
  })
}
