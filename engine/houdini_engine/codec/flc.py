"""Decodificador de animaciones **FLC/FLI** (Autodesk FLIC) → GIF animado.

Las caras animadas de los asistentes de PC Fútbol 7 (`NGI.pkf`) son ficheros `.FLC`
(magic `0xAF12`; `0xAF11` = FLI antiguo). Formato estándar bien documentado:

  cabecera (128 B): size u32 · magic u16 · frames u16 · w u16 · h u16 · depth u16 …
  luego, por FRAME: size u32 · type u16 (0xF1FA) · nº sub-chunks u16 + sub-chunks
  sub-chunk: size u32 · type u16 · datos
    4  COLOR_256   paleta (paquetes: skip, count(0=256), count*3 RGB)
    11 COLOR_64    paleta con componentes 0-63 (×4 → 0-255)
    7  SS2         delta por líneas (FLC)
    12 LC          delta por líneas (FLI)
    15 BYTE_RUN    RLE del primer frame
    16 COPY        copia cruda w*h
    13 BLACK       todo a 0
    18 PSTAMP      miniatura (se ignora)

Se aplica cada chunk sobre un lienzo indexado (w*h) + paleta, y cada frame se vuelca
como fotograma de un GIF animado (índice 8-bit + paleta).
"""
from __future__ import annotations

import io
import struct

FLI_MAGIC = 0xAF11
FLC_MAGIC = 0xAF12


def is_flc(blob: bytes) -> bool:
    return len(blob) >= 6 and struct.unpack_from("<H", blob, 4)[0] in (FLI_MAGIC, FLC_MAGIC)


def _color_chunk(data: bytes, pal: bytearray, wide: bool) -> None:
    """COLOR_256 (wide=False, 0-255) / COLOR_64 (wide=True, 0-63→×4)."""
    o = 0
    npackets = struct.unpack_from("<H", data, o)[0]
    o += 2
    idx = 0
    for _ in range(npackets):
        skip = data[o]
        count = data[o + 1]
        o += 2
        idx += skip
        if count == 0:
            count = 256
        for _c in range(count):
            r, g, b = data[o], data[o + 1], data[o + 2]
            o += 3
            if wide:
                r, g, b = (r << 2) | (r >> 4), (g << 2) | (g >> 4), (b << 2) | (b >> 4)
            if idx < 256:
                pal[idx * 3:idx * 3 + 3] = bytes((r, g, b))
            idx += 1


def _byte_run(data: bytes, canvas: bytearray, w: int, h: int) -> None:
    """BYTE_RUN: RLE por líneas (el primer byte de cada línea es obsoleto)."""
    o = 0
    for y in range(h):
        o += 1                                   # nº de paquetes (obsoleto, se cuenta por ancho)
        x = 0
        row = y * w
        while x < w:
            n = struct.unpack_from("<b", data, o)[0]
            o += 1
            if n >= 0:                            # n copias del mismo byte
                val = data[o]; o += 1
                canvas[row + x:row + x + n] = bytes((val,)) * n
                x += n
            else:                                 # -n bytes literales
                n = -n
                canvas[row + x:row + x + n] = data[o:o + n]; o += n; x += n


def _delta_ss2(data: bytes, canvas: bytearray, w: int, h: int) -> None:
    """SS2 (DELTA_FLC): líneas con conteo de paquetes; opcodes de salto de línea y
    último byte. Cada paquete: skip, size (>=0 literal ×2 bytes / <0 repetir 1 word)."""
    o = 0
    lines = struct.unpack_from("<H", data, o)[0]
    o += 2
    y = 0
    for _ in range(lines):
        while True:
            opcode = struct.unpack_from("<H", data, o)[0]
            o += 2
            typ = opcode >> 14
            if typ == 0:                          # nº de paquetes de esta línea
                npk = opcode & 0x3FFF
                break
            if typ == 2:                          # fija el último byte (píxel impar)
                canvas[y * w + (w - 1)] = opcode & 0xFF
            elif typ == 3:                        # saltar líneas (opcode negativo)
                y += (0x10000 - opcode)
        x = 0
        row = y * w
        for _p in range(npk):
            skip = data[o]; sz = struct.unpack_from("<b", data, o + 1)[0]; o += 2
            x += skip
            if sz >= 0:                           # sz words literales (2 bytes c/u)
                canvas[row + x:row + x + sz * 2] = data[o:o + sz * 2]
                o += sz * 2; x += sz * 2
            else:                                 # repetir 1 word -sz veces
                word = data[o:o + 2]; o += 2
                canvas[row + x:row + x + (-sz) * 2] = word * (-sz)
                x += (-sz) * 2
        y += 1


def decode(blob: bytes) -> tuple[list[bytes], bytearray, int, int, int]:
    """(frames indexados, paleta 768 B, w, h, speed_ms). Cada frame = w*h bytes."""
    _size, magic, nframes, w, h, _depth = struct.unpack_from("<IHHHHH", blob, 0)
    if magic not in (FLI_MAGIC, FLC_MAGIC):
        raise ValueError("no es un FLC/FLI")
    speed = struct.unpack_from("<I", blob, 16)[0] if magic == FLC_MAGIC else \
        struct.unpack_from("<H", blob, 16)[0]
    canvas = bytearray(w * h)
    pal = bytearray(768)
    frames: list[bytes] = []
    o = 128
    n = len(blob)
    while o + 6 <= n and len(frames) <= nframes:
        fsize, ftype = struct.unpack_from("<IH", blob, o)
        if ftype != 0xF1FA:                       # 0xF100 = prefijo (se salta)
            o += fsize if fsize else 6
            continue
        nchunks = struct.unpack_from("<H", blob, o + 6)[0]
        co = o + 16                               # tras la cabecera de frame (16 B)
        for _ in range(nchunks):
            if co + 6 > n:
                break
            csize, ctype = struct.unpack_from("<IH", blob, co)
            cdata = blob[co + 6:co + csize]
            if ctype == 4:
                _color_chunk(cdata, pal, wide=False)
            elif ctype == 11:
                _color_chunk(cdata, pal, wide=True)
            elif ctype == 15:
                _byte_run(cdata, canvas, w, h)
            elif ctype == 7:
                _delta_ss2(cdata, canvas, w, h)
            elif ctype == 13:
                canvas = bytearray(w * h)
            elif ctype == 16:
                canvas[:w * h] = cdata[:w * h]
            # 18 PSTAMP y otros: se ignoran
            co += csize
        frames.append(bytes(canvas))
        o += fsize
    return frames, pal, w, h, max(speed, 20)


def to_gif(blob: bytes) -> bytes | None:
    """FLC → GIF animado (para previsualizar)."""
    from PIL import Image
    frames, pal, w, h, speed = decode(blob)
    if not frames:
        return None
    imgs = []
    for fr in frames:
        im = Image.frombytes("P", (w, h), fr)
        im.putpalette(bytes(pal))
        imgs.append(im)
    buf = io.BytesIO()
    imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:],
                 duration=speed, loop=0, disposal=1)
    return buf.getvalue()


def to_png(blob: bytes, frame: int = 0) -> bytes | None:
    """Un fotograma del FLC como PNG (miniatura)."""
    from PIL import Image
    frames, pal, w, h, _speed = decode(blob)
    if not frames:
        return None
    im = Image.frombytes("P", (w, h), frames[min(frame, len(frames) - 1)])
    im.putpalette(bytes(pal))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG")
    return buf.getvalue()
