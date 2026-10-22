// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/api/client', () => ({ apiFetch: vi.fn() }))

import { apiFetch } from '@/api/client'
import type { Case, Checkout } from '@/api/types'
import { payForPack } from './payments'

const RZP: Checkout = {
  provider: 'razorpay',
  key_id: 'rzp_test_key',
  order_id: 'order_1',
  amount: 39900,
  currency: 'INR',
  name: 'Kavach appeal pack',
}

const CASE = { id: 'c1', paid_at: '2026-10-17T10:00:00Z' } as Case

/** Stand-in for checkout.js: records the options we hand it, opens nothing. */
class FakeRazorpay {
  static last: FakeRazorpay | null = null
  options: Record<string, never> & {
    handler: (r: Record<string, string>) => void
    modal?: { ondismiss?: () => void }
  }

  constructor(options: FakeRazorpay['options']) {
    this.options = options
    FakeRazorpay.last = this
  }

  open() {
    /* the real widget opens an iframe here */
  }
}

const fetchMock = vi.mocked(apiFetch)

beforeEach(() => {
  FakeRazorpay.last = null
  fetchMock.mockReset()
  window.Razorpay = FakeRazorpay as unknown as Window['Razorpay']
})

describe('payForPack', () => {
  it('opens Razorpay and only resolves once the server has verified the signature', async () => {
    fetchMock.mockResolvedValueOnce(RZP).mockResolvedValueOnce(CASE)

    const paying = payForPack('c1', '+919493925966')
    await vi.waitFor(() => expect(FakeRazorpay.last).not.toBeNull())

    // The order we asked the backend to create, with the patient's number prefilled.
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/cases/c1/checkout', { method: 'POST' })
    expect(FakeRazorpay.last!.options).toMatchObject({
      key: 'rzp_test_key',
      order_id: 'order_1',
      amount: 39900,
      currency: 'INR',
      prefill: { contact: '+919493925966' },
    })

    // What checkout.js hands back on success. The case is only ours after the POST below.
    FakeRazorpay.last!.options.handler({
      razorpay_order_id: 'order_1',
      razorpay_payment_id: 'pay_1',
      razorpay_signature: 'sig_1',
    })

    await expect(paying).resolves.toBe(CASE)
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/cases/c1/payment/razorpay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: 'order_1',
        payment_id: 'pay_1',
        signature: 'sig_1',
      }),
    })
  })

  it('resolves null when the patient closes checkout without paying', async () => {
    fetchMock.mockResolvedValueOnce(RZP)

    const paying = payForPack('c1')
    await vi.waitFor(() => expect(FakeRazorpay.last).not.toBeNull())

    FakeRazorpay.last!.options.modal?.ondismiss?.()

    await expect(paying).resolves.toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(1) // never claimed the case was paid
  })

  it('rejects when the server refuses the signature', async () => {
    fetchMock.mockResolvedValueOnce(RZP).mockRejectedValueOnce(new Error("We couldn't verify that payment."))

    const paying = payForPack('c1')
    await vi.waitFor(() => expect(FakeRazorpay.last).not.toBeNull())
    FakeRazorpay.last!.options.handler({
      razorpay_order_id: 'order_1',
      razorpay_payment_id: 'pay_1',
      razorpay_signature: 'forged',
    })

    await expect(paying).rejects.toThrow("couldn't verify")
  })

  it('sends the patient to Stripe and resolves null, leaving the unlock to the webhook', async () => {
    // A hash URL keeps jsdom's navigation happy while still proving assign() was called.
    fetchMock.mockResolvedValueOnce({ provider: 'stripe', url: '#stripe-checkout', amount: 3900, currency: 'SGD' })

    await expect(payForPack('c1')).resolves.toBeNull()
    expect(window.location.hash).toBe('#stripe-checkout')
    // Critically: the browser must NOT be trusted to mark the case paid.
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
