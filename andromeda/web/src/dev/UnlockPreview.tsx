import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiFetch } from '@/api/client'
import type { PackInfo } from '@/api/types'
import { UnlockPanel } from '@/screens/workspace/Panels/UnlockPanel'

/**
 * Dev-only: the appeal-pack paywall for a case on a local backend with PAYMENTS_ENABLED=true.
 * Fetches the pack directly: preview mode seeds the query cache with fixture packs (no price).
 */
export function UnlockPreview() {
  const { caseId = '', country = 'IN' } = useParams()
  const [pack, setPack] = useState<PackInfo | null>(null)
  useEffect(() => {
    apiFetch<PackInfo>(`/packs/${country}`).then(setPack, () => setPack(null))
  }, [country])
  if (!pack?.price_amount) return <p className="p-8 text-sm">Payments are off on this backend.</p>
  return (
    <div className="mx-auto w-full max-w-[760px] px-5 py-8">
      <UnlockPanel caseId={caseId} price={pack} />
    </div>
  )
}
