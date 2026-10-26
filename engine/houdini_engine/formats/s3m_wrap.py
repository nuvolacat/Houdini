"""Genera un módulo ScreamTracker 3 (`.S3M`) que "envuelve" audio ya mezclado.

Sirve para meter una canción normal (MP3/WAV) en PCF 7, cuya música es formato
tracker: se guarda el audio como uno o dos SAMPLES de 8 bits y un patrón que los dispara
(y hace bucle). NO es música tracker real (no separa instrumentos), es un "sample rip":
suena la canción tal cual pero a 8 bits (retro).

- **Estéreo:** dos samples (L y R) en dos canales paneados duro izquierda/derecha (igual que
  los S3M originales del juego). Mono: un solo sample centrado.
- **Multi-capa (efecto espacial):** varias "voces" (samples) cada una en su paneo (centro,
  izq, der…) sonando a la vez — para colocar percusión al centro, un efecto a la derecha, etc.

LÍMITE del formato: los parapointers de instrumentos/patrones son u16 (~1 MB) → se colocan
ANTES; los datos de sample van AL FINAL (memseg de 24 bits, hasta 256 MB). El decode de
audio a PCM 8-bit lo hace la capa API con ffmpeg; aquí solo se ensamblan bytes.
"""
from __future__ import annotations

import struct

# paneo (valor del canal en la cabecera S3M): 0x00 = izquierda, 0x08 = derecha.
# Para "centro" se usan dos canales (izq+der) con la misma muestra.
PAN_LEFT = 0x00
PAN_RIGHT = 0x08


def _align16(b: bytes) -> bytes:
    return b + b"\x00" * ((-len(b)) % 16)


def build(voices: list[tuple[bytes, int]], rate: int, title: str = "Houdini",
          speed: int = 6, tempo: int = 125) -> bytes:
    """Construye el .S3M. `voices` = lista de (muestras_u8, paneo) — cada una un sample de
    8 bits sin signo que se dispara en un canal con ese paneo (0x00 izq / 0x08 der). Todas
    empiezan a la vez en la fila 0 y suenan mezcladas. Devuelve los bytes del módulo."""
    if not voices:
        raise ValueError("sin voces")
    nch = len(voices)
    maxlen = max(len(v) for v, _ in voices)
    dur = maxlen / max(1, rate)
    patdur = 64 * speed * (2.5 / tempo)
    K = int(dur / patdur) + 2                      # patrones vacíos para que suene sin re-disparar

    orders = bytes([0] + [1] * K)
    if len(orders) % 2:
        orders += b"\xff"
    ordnum, insnum, patnum = len(orders), nch, 2

    h = bytearray(96)
    t = title.encode("latin-1", "replace")[:27]
    h[0:len(t)] = t
    h[28] = 0x1A
    h[29] = 0x10
    struct.pack_into("<H", h, 32, ordnum)
    struct.pack_into("<H", h, 34, insnum)
    struct.pack_into("<H", h, 36, patnum)
    struct.pack_into("<H", h, 40, 0x1320)          # cwtv (ST3.20)
    struct.pack_into("<H", h, 42, 2)               # ffi = 2 (muestras unsigned)
    h[44:48] = b"SCRM"
    h[48], h[49], h[50], h[51] = 64, speed, tempo, 0xB0   # gvol, speed, tempo, mastervol (estéreo)
    for c in range(32):
        h[64 + c] = voices[c][1] if c < nch else 0xFF     # paneo por canal ; resto desactivado

    body = bytearray(h)
    body += orders
    ins_pp = len(body); body += b"\x00" * 2 * insnum
    pat_pp = len(body); body += b"\x00" * 2 * patnum
    body = bytearray(_align16(bytes(body)))

    # instrumentos (cabeceras) — ANTES de los samples
    ins_off = []
    for i, (v, _pan) in enumerate(voices):
        off = len(body)
        inst = bytearray(80)
        inst[0] = 1
        inst[0x1c] = 64
        inst[0x1f] = 0
        struct.pack_into("<I", inst, 0x10, len(v))     # longitud
        struct.pack_into("<I", inst, 0x20, rate)       # C2SPD
        inst[0x4c:0x50] = b"SCRS"
        body += inst
        body = bytearray(_align16(bytes(body)))
        ins_off.append(off)
        struct.pack_into("<H", body, ins_pp + 2 * i, off // 16)

    # patrón 0: dispara nota C-4 + su instrumento en cada canal, fila 0
    rows = bytearray()
    for c in range(nch):
        rows += bytes([0x20 | c, 0x40, c + 1])
    rows += bytes([0x00]) + bytes([0x00] * 63)         # fin de fila + 63 filas vacías
    pat0 = struct.pack("<H", len(rows)) + bytes(rows)
    p0 = len(body); body += _align16(pat0)
    pat1 = struct.pack("<H", 64) + bytes([0x00] * 64)
    p1 = len(body); body += _align16(pat1)
    struct.pack_into("<H", body, pat_pp, p0 // 16)
    struct.pack_into("<H", body, pat_pp + 2, p1 // 16)

    # datos de sample AL FINAL (memseg 24 bits)
    for i, (v, _pan) in enumerate(voices):
        smp = len(body)
        body += bytes(v)
        body = bytearray(_align16(bytes(body)))
        seg = smp // 16
        struct.pack_into("<H", body, ins_off[i] + 0x0e, seg & 0xFFFF)
        body[ins_off[i] + 0x0d] = (seg >> 16) & 0xFF

    return bytes(body)


def build_stereo(left: bytes, right: bytes, rate: int, title: str = "Houdini") -> bytes:
    """Canción estéreo: sample L a la izquierda + sample R a la derecha."""
    return build([(left, PAN_LEFT), (right, PAN_RIGHT)], rate, title)
