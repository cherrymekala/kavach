import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { caseKey } from '@/api/hooks'

/** How long we keep waiting for the webhook before handing the screen back. */
const GIVE_UP_MS = 90_000
/** The webhook usually lands within a couple of seconds of the redirect. */
const POLL_MS = 2_500

/** True when Stripe sent us back from a successful checkout. */
export function hasPaidFlag(search: string): boolean {
  return new URLSearchParams(search).get('paid') === '1'
}

/**
 * The same URL without `paid`, so a refresh doesn't resurrect the banner.
 * Exported to be tested directly: getting this wrong either drops other query params or leaves
 * the banner reappearing on every reload.
 */
export function withoutPaidFlag(pathname: string, search: string, hash: string): string {
  const params = new URLSearchParams(search)
  params.delete('paid')
  const query = params.toString()
  return `${pathname}${query ? `?${query}` : ''}${hash}`
}

/**
 * Stripe sends the patient back to `/case/<id>?paid=1`, but the case is only unlocked when
 * Stripe's `checkout.session.completed` webhook arrives — a few seconds later, or never if
 * Firestore isn't configured locally. Without this the patient returns from paying to a screen
 * that still asks them to pay.
 *
 * The flag is read once during render (so nothing has to be set from an effect), stripped from
 * the URL, and the case is refetched until `paid_at` appears or we give up quietly.
 */
export function usePaymentReturn(caseId: string | undefined, paid: boolean): boolean {
  const queryClient = useQueryClient()
  // Which case, if any, we were just redirected back to. Computed on mount, never re-set.
  const [returnedFor] = useState<string | null>(() =>
    caseId && hasPaidFlag(window.location.search) ? caseId : null,
  )
  const [expired, setExpired] = useState(false)

  // Remove the flag as soon as it has been read: a reload should show the normal screen.
  useEffect(() => {
    if (returnedFor !== caseId) return
    const url = new URL(window.location.href)
    window.history.replaceState({}, '', withoutPaidFlag(url.pathname, url.search, url.hash))
  }, [returnedFor, caseId])

  const confirming = returnedFor === caseId && !paid && !expired

  // Poll until the webhook lands. The timeout fires asynchronously, so this stays free of
  // setState-during-render warnings and stops on its own.
  useEffect(() => {
    if (!confirming) return
    const poll = window.setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
    }, POLL_MS)
    const stop = window.setTimeout(() => setExpired(true), GIVE_UP_MS)
    return () => {
      window.clearInterval(poll)
      window.clearTimeout(stop)
    }
  }, [confirming, caseId, queryClient])

  return confirming
}
