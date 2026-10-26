"""Sonidos crudos de PCF — PCM `.RAW` 8-bit SIN signo, mono, 11.025 Hz, sin cabecera.

El silencio es 0x80. La frecuencia no viene escrita (el ejecutable la fija): 11.025 Hz
(confirmado por el pico espectral del silbato del árbitro, FUTBOL_RELOAD). Para reproducir/
descargar se envuelve en un WAV sin tocar las muestras; para importar se acepta cualquier
WAV PCM (8/16 bits, mono/estéreo, cualquier frecuencia) → mono + remuestreo a 11.025 + 8-bit.

Sin dependencias externas ni `audioop` (eliminado en Python 3.13): solo `wave` y remuestreo
lineal manual. Reutilizable por todas las versiones (los otros PCF también tienen sonidos).
"""
from __future__ import annotations

import array
import io
import struct
import wave

FREQ = 11025


def raw_to_wav(raw: bytes, freq: int = FREQ) -> bytes:
    """Envuelve muestras 8-bit sin signo mono en un WAV (sin alterarlas)."""
    n = len(raw)
    out = io.BytesIO()
    out.write(b"RIFF")
    out.write(struct.pack("<I", 36 + n))
    out.write(b"WAVEfmt ")
    out.write(struct.pack("<IHHIIHH", 16, 1, 1, freq, freq, 1, 8))
    out.write(b"data")
    out.write(struct.pack("<I", n))
    out.write(raw)
    return out.getvalue()


def _samples_from_wav(wav: bytes) -> tuple[list[float], int]:
    """Muestras normalizadas [-1..1] (mono) y su frecuencia."""
    w = wave.open(io.BytesIO(wav), "rb")
    ch = w.getnchannels()
    sw = w.getsampwidth()
    fr = w.getframerate()
    data = w.readframes(w.getnframes())
    w.close()
    out: list[float] = []
    if sw == 1:                                    # 8-bit sin signo (centro 0x80)
        step = ch
        for i in range(0, len(data) - ch + 1, step):
            s = sum(data[i + c] - 128 for c in range(ch)) / ch
            out.append(s / 127.0)                  # /127 → round-trip 8-bit sin pérdida
    elif sw == 2:                                  # 16-bit con signo
        a = array.array("h")
        usable = (len(data) // (2 * ch)) * (2 * ch)
        a.frombytes(data[:usable])
        for i in range(0, len(a) - ch + 1, ch):
            s = sum(a[i + c] for c in range(ch)) / ch
            out.append(s / 32768.0)
    else:
        raise ValueError("WAV no soportado (usa PCM de 8 o 16 bits)")
    return out, fr


def _resample(samples: list[float], src: int, dst: int) -> list[float]:
    if src == dst or not samples:
        return samples
    ratio = dst / src
    n = max(1, int(len(samples) * ratio))
    last = len(samples) - 1
    res = [0.0] * n
    for i in range(n):
        pos = i / ratio
        i0 = int(pos)
        frac = pos - i0
        s0 = samples[i0]
        s1 = samples[i0 + 1] if i0 < last else s0
        res[i] = s0 + (s1 - s0) * frac
    return res


def wav_to_raw(wav: bytes, freq: int = FREQ) -> bytes:
    """Cualquier WAV PCM → muestras 8-bit sin signo mono a `freq` (listas para el `.RAW`)."""
    samples, fr = _samples_from_wav(wav)
    samples = _resample(samples, fr, freq)
    out = bytearray(len(samples))
    for i, s in enumerate(samples):
        v = int(round(s * 127)) + 128
        out[i] = 0 if v < 0 else 255 if v > 255 else v
    return bytes(out)


def duration_seconds(raw: bytes, freq: int = FREQ) -> float:
    return len(raw) / freq if freq else 0.0
