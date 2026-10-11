/** Microphone capture (16 kHz PCM16) and gapless playback (24 kHz PCM16) for the hearing. */

export function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  }
  return btoa(binary)
}

function fromBase64(data: string): Int16Array {
  const binary = atob(data)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new Int16Array(bytes.buffer)
}

export class Recorder {
  private ctx?: AudioContext
  private stream?: MediaStream
  private node?: AudioWorkletNode

  /** Throws if the mic is unavailable or permission is denied. */
  async start(onChunk: (base64: string) => void): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    })
    this.ctx = new AudioContext()
    await this.ctx.audioWorklet.addModule('/audio/recorder-worklet.js')
    this.node = new AudioWorkletNode(this.ctx, 'recorder-processor')
    this.node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onChunk(toBase64(e.data))
    this.ctx.createMediaStreamSource(this.stream).connect(this.node)
  }

  stop(): void {
    this.node?.disconnect()
    this.stream?.getTracks().forEach((t) => t.stop())
    void this.ctx?.close()
    this.node = undefined
    this.stream = undefined
    this.ctx = undefined
  }
}

export class Player {
  private ctx = new AudioContext({ sampleRate: 24000 })
  private next = 0
  private sources = new Set<AudioBufferSourceNode>()

  /** Call from a click handler so mobile browsers allow sound. */
  resume(): Promise<void> {
    return this.ctx.resume()
  }

  play(base64: string): void {
    const pcm = fromBase64(base64)
    const buffer = this.ctx.createBuffer(1, pcm.length, 24000)
    const channel = buffer.getChannelData(0)
    for (let i = 0; i < pcm.length; i++) channel[i] = pcm[i] / 32768
    const source = this.ctx.createBufferSource()
    source.buffer = buffer
    source.connect(this.ctx.destination)
    this.next = Math.max(this.next, this.ctx.currentTime + 0.05)
    source.start(this.next)
    this.next += buffer.duration
    this.sources.add(source)
    source.onended = () => this.sources.delete(source)
  }

  get speaking(): boolean {
    return this.sources.size > 0
  }

  /** Stop whatever is queued (the patient started talking). */
  interrupt(): void {
    this.sources.forEach((s) => s.stop())
    this.sources.clear()
    this.next = 0
  }

  close(): void {
    this.interrupt()
    void this.ctx.close()
  }
}
