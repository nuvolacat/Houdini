"""IFF ILBM (InterLeaved BitMap) — el formato de Deluxe Paint/Amiga.

Es el formato de las **pantallas del launcher/actualizador de PC Fútbol 4.0** (contenedores
`PCFTEX4.DAT`, `PCFTEX.DAT`, `LGR.DAT`): varios `FORM …… ILBM` concatenados sin índice
externo (se leen secuencialmente por el tamaño que declara cada FORM).

Estructura de un FORM ILBM:
- `FORM` + tamaño(u32 BE) + `ILBM`
- chunk `BMHD` (20B): w,h (u16 BE), x,y (i16), nPlanes(u8), masking, compression, pad,
  transparentColor(u16), xAspect, yAspect, pageW, pageH (i16). compression 1 = ByteRun1.
- chunk `CMAP`: paleta, 3 bytes RGB por color (aquí 16 colores, 8 bits por canal).
- chunk `BODY`: bitmap **planar** — por cada fila, `nPlanes` planos de `rowbytes` bytes
  (`rowbytes = ((w+15)//16)*2`, alineado a word); bit 7 = píxel izquierdo. Con compresión
  ByteRun1 (PackBits) el BODY va comprimido.

Todos los enteros multi-byte de IFF son **big-endian**.
"""
from __future__ import annotations

import io
import struct

from PIL import Image


# ------------------------------------------------------------- ByteRun1 (PackBits)
def _unpack(src: bytes, need: int) -> bytes:
    out = bytearray()
    i, n = 0, len(src)
    while i < n and len(out) < need:
        c = src[i]
        i += 1
        if c < 128:                       # copiar los siguientes c+1 bytes
            out += src[i:i + c + 1]
            i += c + 1
        elif c > 128:                     # repetir el siguiente byte 257-c veces
            out += bytes([src[i]]) * (257 - c)
            i += 1
        # c == 128 → NOP
    return bytes(out)


def _pack_row(row: bytes) -> bytes:
    """PackBits de UNA fila (se resetea en cada fila, como Deluxe Paint)."""
    out = bytearray()
    i, n = 0, len(row)
    while i < n:
        # ¿run de 3+ iguales?
        run = 1
        while i + run < n and row[i + run] == row[i] and run < 128:
            run += 1
        if run >= 3:
            out.append(257 - run)
            out.append(row[i])
            i += run
        else:
            # literal: acumular hasta el próximo run de 3+
            j = i
            lit = bytearray()
            while j < n and len(lit) < 128:
                r = 1
                while j + r < n and row[j + r] == row[j] and r < 3:
                    r += 1
                if r >= 3:
                    break
                lit.append(row[j])
                j += 1
            out.append(len(lit) - 1)
            out += lit
            i = j
    return bytes(out)


# ------------------------------------------------------------- FORMs del contenedor
def iter_forms(data: bytes) -> list[tuple[int, int]]:
    """[(offset, tamaño_total_incl_cabecera)] de cada FORM…ILBM del contenedor."""
    out: list[tuple[int, int]] = []
    o, n = 0, len(data)
    while o + 12 <= n:
        if data[o:o + 4] == b"FORM" and data[o + 8:o + 12] in (b"ILBM", b"PBM "):
            sz = struct.unpack_from(">I", data, o + 4)[0]
            total = 8 + sz + (sz & 1)
            out.append((o, total))
            o += total
        else:
            o += 1
    return out


def _chunks(body: bytes):
    """Itera los chunks del FORM (body = todo tras 'FORM'<size>, empieza en 'ILBM')."""
    o, n = 4, len(body)                    # saltar 'ILBM'
    while o + 8 <= n:
        cid = body[o:o + 4]
        sz = struct.unpack_from(">I", body, o + 4)[0]
        yield cid, o + 8, sz               # (id, offset del contenido, tamaño)
        o += 8 + sz + (sz & 1)


def parse_form(data: bytes, off: int, size: int) -> dict:
    """Metadatos + offsets del FORM en `off`. `body` = data[off+8 : off+size]."""
    body = data[off + 8:off + size]
    info: dict = {"w": 0, "h": 0, "nplanes": 0, "comp": 0, "cmap": None,
                  "body_off": 0, "body_len": 0, "type": body[:4]}
    for cid, co, sz in _chunks(body):
        if cid == b"BMHD":
            w, h, _x, _y, npl, _mask, comp = struct.unpack_from(">HHhhBBB", body, co)
            if w * h > 16 * 1024 * 1024:   # cota anti-bomba (imágenes reales del juego son ≪)
                raise ValueError("ILBM: dimensiones excesivas")
            info.update(w=w, h=h, nplanes=npl, comp=comp)
        elif cid == b"CMAP":
            info["cmap"] = body[co:co + sz]
        elif cid == b"BODY":
            info["body_off"] = off + 8 + co      # offset ABSOLUTO en `data`
            info["body_len"] = sz
    return info


def _palette(cmap: bytes | None) -> list[tuple[int, int, int]]:
    if not cmap:
        return [(i, i, i) for i in range(256)]
    pal = [(cmap[i * 3], cmap[i * 3 + 1], cmap[i * 3 + 2]) for i in range(len(cmap) // 3)]
    while len(pal) < 256:
        pal.append((0, 0, 0))
    return pal


def _planar_to_indices(raw: bytes, w: int, h: int, npl: int) -> bytearray:
    rb = ((w + 15) // 16) * 2
    idx = bytearray(w * h)
    p = 0
    for row in range(h):
        planes = [raw[p + k * rb: p + (k + 1) * rb] for k in range(npl)]
        p += rb * npl
        base = row * w
        for x in range(w):
            by = x >> 3
            bit = 7 - (x & 7)
            v = 0
            for k in range(npl):
                if planes[k][by] >> bit & 1:
                    v |= 1 << k
            idx[base + x] = v
    return idx


def decode(data: bytes, off: int, size: int) -> Image.Image:
    """Decodifica el FORM en `off` a una imagen PIL RGB."""
    info = parse_form(data, off, size)
    w, h, npl, comp = info["w"], info["h"], info["nplanes"], info["comp"]
    rb = ((w + 15) // 16) * 2
    body = data[info["body_off"]:info["body_off"] + info["body_len"]]
    raw = _unpack(body, rb * npl * h) if comp == 1 else body
    idx = _planar_to_indices(raw, w, h, npl)
    im = Image.frombytes("P", (w, h), bytes(idx))
    flat: list[int] = []
    for c in _palette(info["cmap"]):
        flat += list(c)
    im.putpalette(flat)
    return im.convert("RGB")


def decode_png(data: bytes, off: int, size: int) -> bytes:
    buf = io.BytesIO()
    decode(data, off, size).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------- encode
def _nearest(pal: list[tuple[int, int, int]], rgb: tuple[int, int, int],
             cache: dict) -> int:
    v = cache.get(rgb)
    if v is not None:
        return v
    r, g, b = rgb
    best, bi = 1 << 30, 0
    for i in range(len(pal)):
        pr, pg, pb = pal[i]
        dd = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dd < best:
            best, bi = dd, i
            if dd == 0:
                break
    cache[rgb] = bi
    return bi


def _indices_to_planar(idx: bytes, w: int, h: int, npl: int) -> bytes:
    rb = ((w + 15) // 16) * 2
    out = bytearray(rb * npl * h)
    for row in range(h):
        base = row * w
        pbase = row * rb * npl
        for x in range(w):
            v = idx[base + x]
            if not v:
                continue
            by = x >> 3
            mask = 1 << (7 - (x & 7))
            for k in range(npl):
                if v >> k & 1:
                    out[pbase + k * rb + by] |= mask
    return bytes(out)


def encode_body(png: bytes, w: int, h: int, npl: int,
                palette: list[tuple[int, int, int]], comp: int) -> bytes:
    """Cuantiza `png` a la paleta (w×h), lo pasa a planar y devuelve el BODY (comprimido
    ByteRun1 si comp==1)."""
    src = Image.open(io.BytesIO(png)).convert("RGB")
    if src.size != (w, h):
        src = src.resize((w, h), Image.LANCZOS)
    sp = src.load()
    pal = palette[:1 << npl]
    cache: dict = {}
    idx = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            idx[y * w + x] = _nearest(pal, sp[x, y], cache)
    planar = _indices_to_planar(bytes(idx), w, h, npl)
    if comp != 1:
        return planar
    rb = ((w + 15) // 16) * 2
    out = bytearray()
    for row in range(h):
        out += _pack_row(planar[row * rb * npl:(row + 1) * rb * npl])
    return bytes(out)


def build_form(w: int, h: int, npl: int, cmap: bytes, body: bytes, comp: int) -> bytes:
    """Construye un FORM ILBM completo (BMHD+CMAP+BODY) desde cero."""
    bmhd = struct.pack(">HHhhBBBBHBBhh", w, h, 0, 0, npl, 0, comp, 0, 0, 1, 1, w, h)

    def chunk(cid: bytes, payload: bytes) -> bytes:
        out = cid + struct.pack(">I", len(payload)) + payload
        if len(payload) & 1:
            out += b"\x00"                 # padding a word
        return out

    inner = b"ILBM" + chunk(b"BMHD", bmhd) + chunk(b"CMAP", cmap) + chunk(b"BODY", body)
    return b"FORM" + struct.pack(">I", len(inner)) + inner
