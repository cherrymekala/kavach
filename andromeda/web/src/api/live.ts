import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db, isConfigured } from '@/firebase'
import type { Case } from './types'

export interface LiveCase {
  data: Case | null
  error: string | null
}

/** Live case doc from Firestore (progress + status + events) — read-only. */
export function useLiveCase(caseId: string | undefined): LiveCase {
  const [data, setData] = useState<Case | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!caseId || !isConfigured()) return
    const unsubscribe = onSnapshot(
      doc(db(), 'cases', caseId),
      (snap) => setData(snap.exists() ? (snap.data() as Case) : null),
      (err) => setError(err.message),
    )
    return unsubscribe
  }, [caseId])

  return { data, error }
}