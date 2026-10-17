import { apiFetch } from './client'
import type { Case, Checkout } from './types'

interface RazorpayResponse {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void }
  }
}

const RAZORPAY_JS = 'https://checkout.razorpay.com/v1/checkout.js'

function loadRazorpay(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = RAZORPAY_JS
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('Could not load the payment page. Check your connection.'))
    document.head.appendChild(s)
  })
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/**
 * Pay for the appeal pack. India: Razorpay's in-page checkout, then the server checks the
 * signature and returns the unlocked case. Singapore/Malaysia: redirect to Stripe Checkout; the
 * server unlocks the case from Stripe's webhook and the live case listener picks it up.
 * Resolves with the updated case, or null when the page is redirecting / the user closed checkout.
 */
export async function payForPack(caseId: string, phone?: string | null): Promise<Case | null> {
  const checkout = await apiFetch<Checkout>(`/cases/${caseId}/checkout`, { method: 'POST' })
  if (checkout.provider === 'stripe') {
    window.location.assign(checkout.url)
    return null
  }
  await loadRazorpay()
  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay!({
      key: checkout.key_id,
      order_id: checkout.order_id,
      amount: checkout.amount,
      currency: checkout.currency,
      name: 'Kavach',
      description: checkout.name,
      prefill: phone ? { contact: phone } : undefined,
      theme: { color: '#0f4c5c' },
      handler: (r: RazorpayResponse) =>
        apiFetch<Case>(
          `/cases/${caseId}/payment/razorpay`,
          json({ order_id: r.razorpay_order_id, payment_id: r.razorpay_payment_id, signature: r.razorpay_signature }),
        ).then(resolve, reject),
      modal: { ondismiss: () => resolve(null) },
    })
    rzp.open()
  })
}
