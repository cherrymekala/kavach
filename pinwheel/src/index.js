/**
 * Kavach mail Worker (Cloudflare Email Routing → Kavach backend).
 *
 * Every reply to the appeal address arrives here as raw MIME. We parse it and post the parts
 * the backend needs to /mail/inbound (sombrero/src/kavach/routers/mail.py, InboundMail). The
 * backend matches the reply to its case through In-Reply-To / References, so this Worker
 * keeps no state and knows nothing about cases.
 */
import PostalMime from 'postal-mime'

const MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024 // the backend's upload limit

function toBase64(content) {
  const bytes = typeof content === 'string' ? new TextEncoder().encode(content) : new Uint8Array(content)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  }
  return btoa(binary)
}

export async function toInbound(raw) {
  const email = await PostalMime.parse(raw)
  return {
    from: email.from?.address ?? '',
    subject: email.subject ?? '',
    text: email.text ?? '',
    in_reply_to: email.inReplyTo ?? null,
    references: email.references ?? null,
    attachments: (email.attachments ?? [])
      .filter((a) => a.disposition !== 'inline' && a.content && a.content.byteLength <= MAX_ATTACHMENT_BYTES)
      .map((a) => ({ filename: a.filename ?? 'attachment', content: toBase64(a.content), type: a.mimeType })),
  }
}

export default {
  async email(message, env) {
    const body = await toInbound(message.raw)
    const res = await fetch(env.KAVACH_INBOUND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Kavach-Token': env.KAVACH_TOKEN },
      body: JSON.stringify(body),
    })
    // A failed post throws, so Cloudflare reports a temporary failure and the sender retries;
    // a reply is never silently lost.
    if (!res.ok) throw new Error(`Kavach inbound failed: ${res.status}`)
  },
}
