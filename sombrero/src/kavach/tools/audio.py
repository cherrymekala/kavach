"""Phone audio <-> Gemini Live audio, in pure Python (audioop was removed in Python 3.13).

Twilio media streams carry 8 kHz mono G.711 mu-law. Gemini Live takes 16 kHz PCM16 in and
returns 24 kHz PCM16. Phone audio is band-limited to ~3.4 kHz, so linear interpolation up and
averaging down are good enough for speech.
"""

import array
import sys

_BIAS = 0x84
_CLIP = 32635


def _decode_byte(u: int) -> int:
    u = ~u & 0xFF
    t = ((u & 0x0F) << 3) + _BIAS
    t <<= (u & 0x70) >> 4
    return (_BIAS - t) if u & 0x80 else (t - _BIAS)


_DECODE = [_decode_byte(i) for i in range(256)]


def _encode_sample(s: int) -> int:
    sign = 0x80 if s < 0 else 0
    s = min(abs(s), _CLIP) + _BIAS
    exponent = max(s.bit_length() - 8, 0)
    mantissa = (s >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


# Encoding by table: one lookup per sample instead of bit twiddling (index = sample + 32768).
_ENCODE = bytes(_encode_sample(s) for s in range(-32768, 32768))


def _pcm(data: bytes) -> array.array:
    samples = array.array("h", data[: len(data) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()  # PCM16 on the wire is little-endian
    return samples


def _bytes(samples: array.array) -> bytes:
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def ulaw_to_pcm16(data: bytes) -> bytes:
    """8 kHz mu-law -> 8 kHz PCM16 little-endian."""
    return _bytes(array.array("h", (_DECODE[b] for b in data)))


def pcm16_to_ulaw(data: bytes) -> bytes:
    return bytes(_ENCODE[s + 32768] for s in _pcm(data))


def upsample_2x(data: bytes) -> bytes:
    """8 kHz -> 16 kHz PCM16 by linear interpolation."""
    s = _pcm(data)
    out = array.array("h")
    for i, x in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else x
        out.append(x)
        out.append((x + nxt) // 2)
    return _bytes(out)


def downsample_3x(data: bytes) -> bytes:
    """24 kHz -> 8 kHz PCM16 by averaging each group of three samples (a cheap low-pass)."""
    s = _pcm(data)
    n = len(s) // 3 * 3
    return _bytes(array.array("h", ((s[i] + s[i + 1] + s[i + 2]) // 3 for i in range(0, n, 3))))


def phone_to_live(payload: bytes) -> bytes:
    """Twilio media payload -> Gemini Live input (16 kHz PCM16)."""
    return upsample_2x(ulaw_to_pcm16(payload))


def live_to_phone(pcm24k: bytes) -> bytes:
    """Gemini Live output (24 kHz PCM16) -> Twilio media payload (8 kHz mu-law)."""
    return pcm16_to_ulaw(downsample_3x(pcm24k))
