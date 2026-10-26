"""Contenedor de imágenes `.pak` de PCF 2000/2001.

Distinto del `.pkf` de v5/6/7. Estructura (ing. inversa + editor Java de la comunidad):

    offset 0   : magic b"PAK_"
    offset 4   : u32 versión (0x100) · offset 8: u32 (0x40000)
    offset 12  : u32 count (nº de entradas)
    offset 16  : índice de `count` entradas de 36 B:
                 u32 init (offset del bloque) · u32 length · u32 (ignorado) ·
                 24 B ruta CIFRADA (XOR de clave incremental: byte[i] ^ ((0x94+i)&0xFF)),
                 p.ej. "MINIESC\\eq980001.bmp"
    bloques    : cada uno es un **BMP estándar** (a veces con compresión BI_RLE8).

El juego también lee BMP sueltos en subcarpetas como override (MINIESC\\eq00NNNN.bmp…),
así que para EDITAR no hace falta reempaquetar el .pak; esto es para LEER los originales.
"""
from __future__ import annotations

import io
import re
import struct

from PIL import Image

MAGIC = b"PAK_"
_ENTRY = 36
_PATH_LEN = 24
# La ruta de 24 B va cifrada con XOR de clave INCREMENTAL: byte[i] ^ ((K+i)&0xFF).
# K varía por fichero (0x91–0x95 observados) → se auto-detecta. No es fijo.
_NAME_RE = re.compile(r"[A-Za-z0-9_]+[\\/][A-Za-z0-9_]+\.(bmp|jpg)", re.IGNORECASE)


def _decode_name(pb: bytes, key: int | None) -> str:
    """Descifra la ruta. `key=None` → texto PLANO (PCF2001); int → XOR incremental
    byte[i]^((key+i)&0xFF) (PCF2000)."""
    enc = pb.split(b"\x00")[0]                          # la ruta real acaba en null
    if key is None:
        return enc.decode("latin-1", "replace")
    return bytes((enc[i] ^ ((key + i) & 0xFF)) for i in range(len(enc))).decode("latin-1", "replace")


def detect_key(data: bytes) -> int | None:
    """Auto-detecta el cifrado de ruta probando la 1ª entrada. Devuelve None si las
    rutas van en PLANO (PCF2001), o la clave inicial int del XOR incremental (PCF2000)."""
    pb0 = data[16 + 12:16 + 12 + _PATH_LEN]
    if _NAME_RE.fullmatch(_decode_name(pb0, None)):     # PCF2001: rutas sin cifrar
        return None
    for k in range(256):
        if _NAME_RE.fullmatch(_decode_name(pb0, k)):
            return k
    return 0x94                                         # por defecto (MINIESC de PCF2000)


def index(data: bytes) -> list[tuple[str, int, int]]:
    """[(ruta_interna, init, length)] de todas las entradas del .pak (auto-detecta cifrado)."""
    if data[:4] != MAGIC:
        raise ValueError("no es un contenedor .pak (falta PAK_)")
    key = detect_key(data)
    n = struct.unpack_from("<I", data, 12)[0]
    out = []
    for i in range(n):
        o = 16 + i * _ENTRY
        init, length, _skip = struct.unpack_from("<III", data, o)
        name = _decode_name(data[o + 12:o + 12 + _PATH_LEN], key)
        out.append((name, init, length))
    return out


# flag@8 con bit 0x40000 = nombres CIFRADOS (PCF2000); 0 = texto plano (PCF2001)
_ENC_FLAG = 0x40000
_IMG_EXTS = (".bmp", ".jpg", ".jpeg", ".gif", ".pcx", ".flc", ".fli")


def _detect_prefix_char(data: bytes) -> int:
    """Primer carácter (plaintext) de las rutas cifradas de un PAK. K0 varía por
    entrada pero TODAS empiezan por el mismo char (p.ej. "graficos\\" o "IMG\\").
    Se brute-forcea K0 de la 1ª entrada hasta obtener una ruta plausible."""
    o = 16
    end = data.index(b"\x00", o + 12)
    raw = data[o + 12:end]
    if not raw:
        return ord("g")

    def _plausible(k0: int) -> str | None:
        dec = bytes((raw[i] ^ ((k0 + i) & 0xFF)) for i in range(len(raw)))
        try:
            s = dec.decode("latin-1")
        except Exception:  # noqa: BLE001
            return None
        if "\\" in s and s[0].isalpha() and all(32 <= ord(c) < 127 for c in s):
            return s
        return None

    # 1ª vuelta: rutas de IMAGEN, que es lo que traen los .pak de gráficos. Se deja igual
    # que estaba para no cambiar lo que ya funcionaba.
    for k0 in range(256):
        s = _plausible(k0)
        if s and s.lower().endswith(_IMG_EXTS):
            return ord(s[0])
    # 2ª vuelta: cualquier ruta razonable. Hace falta para `TEXTOS.PAK`, cuyas entradas se
    # llaman «PAISES.22» o «NOMBRES.30» — la extensión es el CÓDIGO DE PAÍS, no un formato
    # de imagen, así que la primera vuelta no encontraba nada y el lector devolvía basura.
    for k0 in range(256):
        s = _plausible(k0)
        if s and "." in s.rsplit("\\", 1)[-1]:
            return ord(s[0])
    return ord("g")                    # respaldo (GRAFICOS)


def index_var(data: bytes) -> list[tuple[str, int, int, int]]:
    """Índice de longitud VARIABLE (formato REAL del `PAK_`): cada entrada =
    init(u32) length(u32) skip(u32) + nombre + **null RAW** (sin cifrar) + padding a 4.
    - PCF2001 (flag 0): nombre en TEXTO PLANO.
    - PCF2000 (flag 0x40000): nombre CIFRADO con XOR incremental, clave K0 POR ENTRADA
      = `primer_byte ^ 'g'` (toda ruta empieza por "graficos\\"; K0 varía por entrada).
    El null es RAW en ambos → delimita sin ambigüedad (para nombres <~130 B el keystream
    nunca produce un 0x00 interno). Devuelve [(ruta, init, length, offset_del_header)].
    MINIESC casaba con el lector fijo de 36 B por azar (nombres cortos que redondean a 36)."""
    if data[:4] != MAGIC:
        raise ValueError("no es un contenedor .pak (falta PAK_)")
    encrypted = bool(struct.unpack_from("<I", data, 8)[0] & _ENC_FLAG)
    prefix0 = _detect_prefix_char(data) if encrypted else 0
    n = struct.unpack_from("<I", data, 12)[0]
    out = []
    o = 16
    for _ in range(n):
        hdr = o
        init, length, _skip = struct.unpack_from("<III", data, o)
        o += 12
        end = data.index(b"\x00", o)          # boundary = null RAW
        raw = data[o:end]
        if encrypted and raw:
            k0 = (raw[0] ^ prefix0) & 0xFF     # K0 por entrada; prefijo común del pak
            name = bytes((raw[i] ^ ((k0 + i) & 0xFF)) for i in range(len(raw))) \
                .decode("latin-1", "replace")
        else:
            name = raw.decode("latin-1", "replace")
        o = (end + 1 + 3) & ~3               # tras el null, alinear a 4
        out.append((name, init, length, hdr))
    return out


def _basename(name: str) -> str:
    return name.replace("\\", "/").split("/")[-1]


def by_pointer(data: bytes, prefix: str) -> dict[int, tuple[int, int]]:
    """dict puntero → (init, length) para entradas cuyo basename empieza por `prefix`
    (p.ej. 'eq98' escudos, 'j98' fotos, 'BA96' banderas). El número tras el prefijo es el
    puntero canónico Dinamic (con ceros a la izquierda)."""
    out: dict[int, tuple[int, int]] = {}
    pl = prefix.lower()
    for name, init, length in index(data):
        b = _basename(name).lower()
        if b.startswith(pl):
            num = b[len(pl):].split(".")[0]
            if num.isdigit():
                out[int(num)] = (init, length)
    return out


# ------------------------------------------------------------------ BMP → PIL
def _decode_rle8(pix: bytes, w: int, h: int, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Decodifica BI_RLE8 (BMP comprimido). Filas de abajo a arriba."""
    out = bytearray(w * h)          # índices de paleta; 0 por defecto
    x = 0
    y = h - 1
    i = 0
    n = len(pix)
    while i + 1 < n and y >= 0:
        cnt = pix[i]; val = pix[i + 1]; i += 2
        if cnt:                                     # run: `cnt` píxeles de color `val`
            for _ in range(cnt):
                if 0 <= x < w and 0 <= y < h:
                    out[y * w + x] = val
                x += 1
        else:                                       # códigos de escape
            if val == 0:                            # fin de línea
                x = 0; y -= 1
            elif val == 1:                          # fin de bitmap
                break
            elif val == 2:                          # delta (dx, dy)
                if i + 1 < n:
                    x += pix[i]; y -= pix[i + 1]; i += 2
            else:                                   # modo absoluto: `val` píxeles literales
                for k in range(val):
                    if i + k < n and 0 <= x < w and 0 <= y < h:
                        out[y * w + x] = pix[i + k]
                    x += 1
                i += val
                if val & 1:                         # alineado a word
                    i += 1
    img = Image.frombytes("P", (w, h), bytes(out))
    flat = []
    for r, g, b in palette:
        flat += [r, g, b]
    flat += [0, 0, 0] * (256 - len(palette))
    img.putpalette(flat)
    return img


def _decode_rle4(pix: bytes, w: int, h: int, palette: list[tuple[int, int, int]]) -> Image.Image:
    """BI_RLE4 (BMP 4-bit comprimido). Como RLE8 pero cada byte = 2 nibbles."""
    out = bytearray(w * h)
    x = 0
    y = h - 1
    i = 0
    n = len(pix)
    while i + 1 < n and y >= 0:
        cnt = pix[i]; val = pix[i + 1]; i += 2
        if cnt:                                     # run: `cnt` píxeles alternando 2 nibbles
            hi, lo = val >> 4, val & 0xF
            for k in range(cnt):
                if 0 <= x < w and 0 <= y < h:
                    out[y * w + x] = hi if (k & 1) == 0 else lo
                x += 1
        elif val == 0:                              # fin de línea
            x = 0; y -= 1
        elif val == 1:                              # fin de bitmap
            break
        elif val == 2:                              # delta
            if i + 1 < n:
                x += pix[i]; y -= pix[i + 1]; i += 2
        else:                                       # absoluto: `val` píxeles (nibbles)
            nbytes = (val + 1) // 2
            for k in range(val):
                byte = pix[i + (k >> 1)] if i + (k >> 1) < n else 0
                nib = (byte >> 4) if (k & 1) == 0 else (byte & 0xF)
                if 0 <= x < w and 0 <= y < h:
                    out[y * w + x] = nib
                x += 1
            i += nbytes
            if nbytes & 1:                          # alineado a word
                i += 1
    return _to_p(out, w, h, palette)


def _to_p(indices: bytearray, w: int, h: int, palette: list) -> Image.Image:
    img = Image.frombytes("P", (w, h), bytes(indices))
    flat = []
    for r, g, b in palette:
        flat += [r, g, b]
    flat += [0, 0, 0] * (256 - len(palette))
    img.putpalette(flat)
    return img


def _decode_bmp_manual(data: bytes) -> Image.Image:
    """Parseo manual de BMP 1/4/8 bpp (comp 0, RLE4 y RLE8) para los que PIL rechaza."""
    if data[:2] != b"BM":
        raise ValueError("no es BMP")
    pix_off = struct.unpack_from("<I", data, 10)[0]
    hdr = struct.unpack_from("<I", data, 14)[0]        # tamaño de la cabecera DIB
    w = struct.unpack_from("<i", data, 18)[0]
    h = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    comp = struct.unpack_from("<I", data, 30)[0]
    if bpp not in (1, 4, 8):
        raise ValueError(f"bpp {bpp} no soportado a mano")
    ncol = struct.unpack_from("<I", data, 46)[0] or (1 << bpp)
    pal_off = 14 + hdr
    palette = []
    for k in range(ncol):
        b, g, r, _ = data[pal_off + k * 4: pal_off + k * 4 + 4]
        palette.append((r, g, b))
    top_down = h < 0
    ah = abs(h)
    pix = data[pix_off:]
    if comp == 1:                                       # BI_RLE8
        return _decode_rle8(pix, w, ah, palette)
    if comp == 2:                                       # BI_RLE4
        return _decode_rle4(pix, w, ah, palette)
    # sin comprimir: filas alineadas a 4 bytes, de abajo a arriba (salvo top-down)
    row = ((w * bpp + 31) // 32) * 4
    out = bytearray(w * ah)
    for ry in range(ah):
        src = ry * row
        dst_y = ry if top_down else (ah - 1 - ry)
        base = dst_y * w
        if bpp == 8:
            out[base:base + w] = pix[src:src + w]
        elif bpp == 4:
            for x in range(w):
                byte = pix[src + (x >> 1)] if src + (x >> 1) < len(pix) else 0
                out[base + x] = (byte >> 4) if (x & 1) == 0 else (byte & 0xF)
        else:                                           # 1 bpp
            for x in range(w):
                byte = pix[src + (x >> 3)] if src + (x >> 3) < len(pix) else 0
                out[base + x] = (byte >> (7 - (x & 7))) & 1
    return _to_p(out, w, ah, palette)


def decode_bmp(data: bytes) -> Image.Image:
    """BMP del juego → PIL Image en modo 'P' (paleta). Prueba PIL y cae al parser manual."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im
    except Exception:  # noqa: BLE001
        return _decode_bmp_manual(data)


def entry_png(data: bytes, init: int, length: int,
              transparent_index: int | None = 0) -> bytes:
    """Decodifica el BMP de una entrada y lo devuelve como PNG. Por defecto hace
    TRANSPARENTE el índice de paleta 0 (fondo de los escudos/fotos)."""
    im = decode_bmp(data[init:init + length])
    if transparent_index is not None and im.mode == "P":
        rgba = im.convert("RGBA")
        px = im.load()
        w, h = im.size
        out = rgba.load()
        for y in range(h):
            for x in range(w):
                if px[x, y] == transparent_index:
                    out[x, y] = (0, 0, 0, 0)
        im = rgba
    else:
        im = im.convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()
