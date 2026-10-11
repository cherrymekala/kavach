// Mic -> 16 kHz mono PCM16 chunks (~100 ms) for the Gemini Live hearing.
// Runs at the AudioContext's own rate (usually 48 kHz) and averages down to 16 kHz.
class RecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.ratio = sampleRate / 16000
    this.pending = 0
    this.acc = 0
    this.count = 0
    this.out = new Int16Array(1600)
    this.len = 0
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (!channel) return true
    for (let i = 0; i < channel.length; i++) {
      this.acc += channel[i]
      this.count++
      this.pending++
      if (this.pending >= this.ratio) {
        this.pending -= this.ratio
        const s = Math.max(-1, Math.min(1, this.acc / this.count))
        this.out[this.len++] = s < 0 ? s * 0x8000 : s * 0x7fff
        this.acc = 0
        this.count = 0
        if (this.len === this.out.length) {
          this.port.postMessage(this.out.buffer.slice(0))
          this.len = 0
        }
      }
    }
    return true
  }
}

registerProcessor('recorder-processor', RecorderProcessor)
