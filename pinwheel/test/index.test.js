import assert from 'node:assert/strict'
import { test } from 'node:test'
import worker, { toInbound } from '../src/index.js'

const pdf = Buffer.from('%PDF-1.4 query').toString('base64')
const raw = [
  'From: Grievance Cell <gro@insurer.example>',
  'To: appeals@kavach.reimaginy.tech',
  'Subject: Re: Appeal against rejection of claim CLI/1',
  'Message-ID: <reply-1@insurer.example>',
  'In-Reply-To: <abc@cloudflare.example>',
  'References: <older@insurer.example> <abc@cloudflare.example>',
  'MIME-Version: 1.0',
  'Content-Type: multipart/mixed; boundary="b1"',
  '',
  '--b1',
  'Content-Type: text/plain; charset=utf-8',
  '',
  'Please share the ultrasound report dated 05/07/2026.',
  '--b1',
  'Content-Type: application/pdf; name="query.pdf"',
  'Content-Disposition: attachment; filename="query.pdf"',
  'Content-Transfer-Encoding: base64',
  '',
  pdf,
  '--b1--',
  '',
].join('\r\n')

test('a MIME reply becomes the JSON the backend expects', async () => {
  const body = await toInbound(raw)
  assert.equal(body.from, 'gro@insurer.example')
  assert.equal(body.subject, 'Re: Appeal against rejection of claim CLI/1')
  assert.match(body.text, /ultrasound report dated/)
  assert.equal(body.in_reply_to, '<abc@cloudflare.example>')
  assert.match(body.references, /<abc@cloudflare\.example>/)
  assert.deepEqual(body.attachments, [{ filename: 'query.pdf', content: pdf, type: 'application/pdf' }])
})

test('the reply is posted with the shared token, and a failed post throws', async () => {
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init })
    return { ok: calls.length === 1, status: calls.length === 1 ? 200 : 503 }
  }
  const env = { KAVACH_INBOUND_URL: 'https://kavach.test/mail/inbound', KAVACH_TOKEN: 's3cret' }
  await worker.email({ raw }, env)
  assert.equal(calls[0].url, env.KAVACH_INBOUND_URL)
  assert.equal(calls[0].init.headers['X-Kavach-Token'], 's3cret')
  assert.equal(JSON.parse(calls[0].init.body).in_reply_to, '<abc@cloudflare.example>')
  await assert.rejects(worker.email({ raw }, env), /503/)
})
