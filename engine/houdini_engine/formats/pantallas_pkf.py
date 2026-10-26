"""Contenedores de PANTALLAS / gráficos de interfaz de PCF 7.

`Recursos.pkf` (fondos, barras, botones), `Img.pkf` (iconos/copas), `DAT.PKF` (paletas RIFF +
tablas), `NGI.pkf` (animaciones FLC de los asistentes). 

Mismo **PKF paginado** que los contenedores de imágenes (`imagenes_pkf`), con tres diferencias:
- El fichero puede ser **varios sub-contenedores CONCATENADOS**, cada uno con su cabecera de 232 B
  (primer byte `0x01`). El índice de cada uno arranca en `base+232`.
- Los offsets del índice son **ABSOLUTOS** al fichero.
- Las entradas se indexan por **NOMBRE libre** de pantalla (BALON.BMP, FONDO7.BMP, MENU.PAL…),
  no por el puntero `EQ96xxxx` de los datos.

Contenido de cada entrada:
- **BMP** 8bpp SIN paleta (magia `DM`/`BM`) → se pinta con una de las paletas de `DAT.PKF`.
- **GIF** (con su propia paleta) → se sirve tal cual.
- **FLC** (Autodesk FLIC, animación) → de momento solo se lista.

EDICIÓN: reemplazo **in-place** — se sobrescribe el hueco del blob (mismas dimensiones ⇒ mismo
tamaño ⇒ encaja exacto; si el nuevo es menor se rellena con ceros). No se tocan offsets ni índice.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import imagenes_pkf as _IP

_HEADER = 232
_ENTRY_LEN = 38
_ANON_LEN = 9         # entrada sin nombre: tag 03 + offset u32 + tamaño u32
_KEY = _IP._KEY


@dataclass
class Entry:
    idx: int          # posición estable en la lista (ID para la API)
    name: str         # nombre de pantalla descifrado (puede venir truncado a 20 B)
    off: int          # offset ABSOLUTO en el fichero
    size: int
    sub: int = 0      # índice del sub-contenedor (agrupa gráficos de la misma sección/paleta)

    @property
    def ext(self) -> str:
        return self.name.rsplit(".", 1)[-1].upper() if "." in self.name else ""


def entries(data: bytes) -> list[Entry]:
    """Todas las entradas del contenedor (recorre los sub-bloques de índice header `0x01`)."""
    out: list[Entry] = []
    base, seen_base, sub, anon = 0, set(), 0, 0
    while base is not None and 0 <= base < len(data) and base not in seen_base:
        seen_base.add(base)
        pos, seen, nxt = base + _HEADER, set(), None
        while 0 <= pos < len(data) - _ANON_LEN and pos not in seen:
            seen.add(pos)
            tag = data[pos]
            if tag == 0x02 and pos < len(data) - _ENTRY_LEN:
                e = data[pos:pos + _ENTRY_LEN]
                name = bytes(b ^ k for b, k in zip(e[1:21], _KEY)).split(b"\x00")[0].decode(
                    "latin-1", "replace")
                off, size = struct.unpack_from("<II", e, 26)
                if 0 <= off < len(data) and 0 < size <= len(data) - off:
                    out.append(Entry(len(out), name, off, size, sub))
                pos += _ENTRY_LEN
            elif tag == 0x03:
                # Entrada ANÓNIMA: `03` + offset u32 + tamaño u32, sin nombre. En PCF7 son los
                # fondos 640×480 de Recursos.pkf; el juego los referencia por posición, no por
                # nombre. Antes el recorredor moría aquí y esas imágenes eran invisibles.
                off, size = struct.unpack_from("<II", data, pos + 1)
                if 0 <= off < len(data) and 0 < size <= len(data) - off:
                    anon += 1
                    out.append(Entry(len(out), f"SIN_NOMBRE_{anon}.BMP", off, size, sub))
                pos += _ANON_LEN
            elif tag == 0x04:
                pos = struct.unpack_from("<I", data, pos + 1)[0]
            elif tag == 0x01 and pos != base:
                nxt = pos
                break
            else:
                break
        base = nxt
        sub += 1
    return out


GRAY_PALETTE = [v for i in range(256) for v in (i, i, i)]   # máscara _ALPHA → escala de grises


def sub_gif_palettes(data: bytes) -> dict[int, dict[str, list[int]]]:
    """{índice de sub-contenedor → {clave: paleta}} de los GIF (sin máscaras _ALPHA) de ese sub.
    Fallback para BMP sin GIF homónimo: usan la paleta de un GIF de su MISMA sección."""
    out: dict[int, dict[str, list[int]]] = {}
    for e in entries(data):
        if "_ALPHA" in e.name.upper():
            continue
        blob = data[e.off:e.off + e.size]
        if blob[:3] == b"GIF":
            p = gif_palette(blob)
            if p:
                out.setdefault(e.sub, {})[f"GIF:{e.name}@{e.off}"] = p
    return out


def kind(name: str, blob: bytes) -> str:
    """'bmp' | 'gif' | 'flc' | 'jpg' | 'pal' | 'other'. El MAGIC manda (el nombre
    del PKF se trunca —p.ej. 'SEGUIMIENTO_ALPHA.B'— y su extensión no es fiable)."""
    ext = name.rsplit(".", 1)[-1].upper() if "." in name else ""
    # 1) por MAGIC (fiable)
    if blob[:3] == b"GIF":
        return "gif"
    if blob[4:6] in (b"\x11\xaf", b"\x12\xaf"):
        return "flc"
    if blob[:4] == b"RIFF":
        return "pal"
    if blob[:2] == b"\xff\xd8":
        return "jpg"
    if blob[:2] in (b"DM", b"BM"):
        return "bmp"
    # 2) respaldo por EXTENSIÓN (si el magic no casa)
    if ext.startswith("GI"):
        return "gif"
    if ext == "FLC":
        return "flc"
    if ext == "PAL":
        return "pal"
    if ext in ("JPG", "JPEG"):
        return "jpg"
    if ext.startswith("B"):                 # BMP / truncado a "B"
        return "bmp"
    return "other"


def bmp_bpp(blob: bytes) -> int:
    """Bits por píxel de un BMP DM/BM (8 indexado, 24 truecolor). 0 si no es BMP."""
    if len(blob) < 26 or blob[:2] not in (b"DM", b"BM"):
        return 0
    bisize = struct.unpack_from("<I", blob, 14)[0]
    return struct.unpack_from("<H", blob, 24 if bisize == 12 else 28)[0]


def truecolor_png(blob: bytes) -> bytes:
    """BMP de 24 bits (RGB, sin paleta) → PNG. Raro (algún gráfico como LIGA HISTORIA/BOLAV_ON)."""
    from io import BytesIO

    from PIL import Image
    bisize = struct.unpack_from("<I", blob, 14)[0]
    if bisize == 12:
        w, h = struct.unpack_from("<HH", blob, 18)
    else:
        w, h = struct.unpack_from("<ii", blob, 18)
    h = abs(h)
    off = struct.unpack_from("<I", blob, 10)[0] or (26 if bisize == 12 else 54)
    stride = (w * 3 + 3) & ~3
    pix = blob[off:]
    if len(pix) < stride * h:
        pix = pix + b"\x00" * (stride * h - len(pix))
    img = Image.frombuffer("RGB", (w, h), pix, "raw", "BGR", stride, -1)   # BGR, bottom-up
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def bmp_dims(blob: bytes) -> tuple[int, int] | None:
    """(ancho, alto) de un blob BMP DM/BM, o None."""
    if len(blob) < 26 or blob[:2] not in (b"DM", b"BM"):
        return None
    bisize = struct.unpack_from("<I", blob, 14)[0]
    if bisize == 40:
        w, h = struct.unpack_from("<ii", blob, 18)
    elif bisize == 12:
        w, h = struct.unpack_from("<HH", blob, 18)
    else:
        return None
    return (abs(w), abs(h))


def _pixel_offset(blob: bytes) -> int:
    bisize = struct.unpack_from("<I", blob, 14)[0]
    return 54 if bisize == 40 else 26


# ---------------------------------------------------------------- paletas RIFF de DAT.PKF
def riff_palette(blob: bytes) -> list[int]:
    """Paleta RIFF PAL (`RIFF..PAL data ver count RGBA[256]`) → lista plana de 256×[r,g,b]."""
    i = blob.find(b"data")
    if i < 0:
        raise ValueError("no es una paleta RIFF")
    base = i + 8 + 4                                   # 'data' + size(4) + ver(2)+count(2)
    pal: list[int] = []
    for c in range(256):
        p = base + c * 4
        if p + 3 <= len(blob):
            pal += [blob[p], blob[p + 1], blob[p + 2]]
        else:
            pal += [0, 0, 0]
    return pal


def palettes(dat: bytes) -> dict[str, list[int]]:
    """Todas las paletas (.PAL) de un DAT.PKF → {nombre_sin_ext: [rgb×256]}."""
    out: dict[str, list[int]] = {}
    for e in entries(dat):
        if e.ext == "PAL":
            try:
                out[e.name.rsplit(".", 1)[0]] = riff_palette(dat[e.off:e.off + e.size])
            except Exception:  # noqa: BLE001
                pass
    return out


def gif_palette(blob: bytes) -> list[int] | None:
    """Paleta embebida de un GIF → [rgb×256], o None. Los GIF de interfaz llevan las paletas
    REALES de cada pantalla (más ricas que las 4 de DAT.PKF)."""
    if blob[:3] != b"GIF":
        return None
    from io import BytesIO

    from PIL import Image
    try:
        p = Image.open(BytesIO(blob)).getpalette()
    except Exception:  # noqa: BLE001
        return None
    if not p:
        return None
    return (list(p) + [0] * 768)[:768]


_SUFFIX = __import__("re").compile(
    r"_(OFF|ON|OVER|SEL|ALPHA|PULSA|PASA|NORMAL|ACT|DESACT|D|E|M|P)$")


def base_name(name: str) -> str:
    """Nombre base de un gráfico quitando sufijos de estado (DESAFIO_OFF → DESAFIO). Sirve para
    emparejar un BMP con el GIF de su MISMA sección (que lleva la paleta correcta embebida)."""
    b = name.rsplit(".", 1)[0].upper()
    prev = None
    while prev != b:
        prev = b
        b = _SUFFIX.sub("", b)
    return b


def named_palettes(datas: list[bytes]) -> dict[str, dict[str, list[int]]]:
    """{nombre_base → {clave: paleta}} de los GIF (excluyendo máscaras _ALPHA). Permite preferir,
    para un BMP, la paleta del GIF homónimo (misma pantalla) — más fiable que la heurística sola.
    Un mismo nombre puede tener varios GIF con paletas distintas (duplicados entre sub-contenedores);
    se guardan todos y luego se elige el mejor con la métrica."""
    out: dict[str, dict[str, list[int]]] = {}
    for data in datas:
        for e in entries(data):
            if "_ALPHA" in e.name.upper():
                continue
            blob = data[e.off:e.off + e.size]
            if blob[:3] == b"GIF":
                p = gif_palette(blob)
                if p:
                    out.setdefault(base_name(e.name), {})[f"GIF:{e.name}@{e.off}"] = p
    return out


def palette_catalog(datas: list[bytes]) -> dict[str, list[int]]:
    """Catálogo de paletas candidatas para auto-mapeo: las RIFF de DAT.PKF + TODAS las distintas
    embebidas en los GIF de los contenedores dados. Clave = 'DAT:NOMBRE' | 'GIF:NOMBRE'."""
    cat: dict[str, list[int]] = {}
    seen: set = set()
    for data in datas:
        for e in entries(data):
            blob = data[e.off:e.off + e.size]
            pal = None
            key = None
            if e.ext == "PAL" and blob[:4] == b"RIFF":
                try:
                    pal = riff_palette(blob)
                    key = "DAT:" + e.name.rsplit(".", 1)[0]
                except Exception:  # noqa: BLE001
                    pal = None
            elif blob[:3] == b"GIF":
                pal = gif_palette(blob)
                key = "GIF:" + e.name
            if pal:
                t = tuple(pal)
                if t not in seen:
                    seen.add(t)
                    cat[key] = pal
    return cat


def _naturalness(pix: bytes, w: int, pal: list[int]) -> float:
    """Puntúa lo "natural" que se ve el BMP bajo `pal` (MÁS alto = mejor). Combina dos señales,
    porque las dos formas de verse mal son opuestas: **ruido** (paleta equivocada → píxeles vecinos
    muy distintos) y **apagado** (paleta que comprime el color → todo gris/muddy, sin contraste).
    La paleta CORRECTA tiene ALTO contraste (texto/fondo bien diferenciados) y POCA diferencia entre
    vecinos (regiones lisas, gradientes suaves): `contraste − 0.5·dif_media`. Muestreo ~4000 px."""
    n = len(pix)
    if n < 2 or w <= 0:
        return -9e18
    step = max(1, n // 4000)
    tot = 0
    cnt = 0
    s = 0.0
    sq = 0.0
    ln = 0
    for i in range(0, n, step):
        p = pix[i] * 3
        lum = 0.299 * pal[p] + 0.587 * pal[p + 1] + 0.114 * pal[p + 2]
        s += lum
        sq += lum * lum
        ln += 1
        if i and i % w:
            a = pix[i] * 3
            b = pix[i - 1] * 3
            tot += abs(pal[a] - pal[b]) + abs(pal[a + 1] - pal[b + 1]) + abs(pal[a + 2] - pal[b + 2])
            cnt += 1
    if not ln or not cnt:
        return -9e18
    mean = s / ln
    contrast = (sq / ln - mean * mean) ** 0.5          # desviación de luminancia (contraste)
    mean_diff = tot / cnt                              # diferencia media entre vecinos (ruido)
    return contrast - 0.5 * mean_diff


def best_palette(blob: bytes, catalog: dict[str, list[int]]) -> tuple[str, list[int]] | None:
    """Auto-elige la paleta del catálogo con la que el BMP se ve más natural (ver `_naturalness`).
    Devuelve (nombre, paleta) o None si no es un BMP o el catálogo está vacío."""
    dims = bmp_dims(blob)
    if not dims or not catalog:
        return None
    w, h = dims
    poff = _pixel_offset(blob)
    pix = blob[poff:poff + w * h]
    best_name, best_pal, best_score = "", None, -9e18
    for name, pal in catalog.items():
        sc = _naturalness(pix, w, pal)
        if sc > best_score:
            best_score, best_name, best_pal = sc, name, pal
    return (best_name, best_pal) if best_pal else None


# ---------------------------------------------------------------- render / import
def to_png(blob: bytes, palette: list[int]) -> bytes:
    """Blob de pantalla → PNG a tamaño nativo. GIF tal cual; BMP 24-bit como RGB; BMP 8-bit con
    la paleta dada."""
    if blob[:3] == b"GIF":
        return blob
    if bmp_bpp(blob) == 24:
        return truecolor_png(blob)
    from io import BytesIO

    from PIL import Image
    bmp = _IP.dm_to_bmp(blob, palette)
    img = Image.open(BytesIO(bmp)).convert("RGB")
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def replace_bmp(orig: bytes, image_bytes: bytes, palette: list[int]) -> bytes:
    """Nuevo blob del MISMO tamaño que `orig`: cabecera BMP original intacta + píxeles nuevos
    (imagen subida redimensionada a las dimensiones originales y cuantizada a `palette`).
    Encaja in-place. Requiere que `orig` sea BMP DM/BM 8bpp."""
    dims = bmp_dims(orig)
    if not dims:
        raise ValueError("el original no es un BMP de pantalla")
    w, h = dims
    from io import BytesIO

    from PIL import Image
    pimg = Image.new("P", (1, 1))
    pal = list(palette[:768]) + [0] * (768 - len(palette))
    pimg.putpalette(pal)
    img = Image.open(BytesIO(image_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
    else:
        img = img.convert("RGB")
    img = img.resize((w, h), Image.LANCZOS)
    q = img.quantize(palette=pimg, dither=Image.FLOYDSTEINBERG)
    rows = q.tobytes()                                  # PIL da filas top-down sin padding
    stride = (w + 3) & ~3
    # BMP guarda las filas BOTTOM-UP y con padding a 4 B
    px = bytearray()
    for y in range(h - 1, -1, -1):
        line = rows[y * w:(y + 1) * w]
        px += line + b"\x00" * (stride - w)
    poff = _pixel_offset(orig)
    body = bytes(px)
    room = len(orig) - poff
    if len(body) > room:                               # el original venía recortado → recortar
        body = body[:room]
    else:
        body = body + b"\x00" * (room - len(body))
    return orig[:poff] + body


def replace_gif(orig: bytes, image_bytes: bytes) -> bytes | None:
    """Nuevo GIF a las MISMAS dimensiones que el original (imagen subida redimensionada + cuantizada
    a ≤256 colores). El GIF es autodelimitado, así que si el nuevo es ≤ el hueco original encaja
    in-place (el resto se rellena con ceros y el lector para en el EOF del GIF). None si falla."""
    from io import BytesIO

    from PIL import Image
    try:
        w, h = Image.open(BytesIO(orig)).size
        img = Image.open(BytesIO(image_bytes))
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
            img = Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
        else:
            img = img.convert("RGB")
        img = img.resize((w, h), Image.LANCZOS)
        out = BytesIO()
        img.save(out, format="GIF", optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return None


def repack_inplace(data: bytes, replacements: dict[int, bytes]) -> bytes:
    """Sobrescribe in-place los blobs indicados (`{offset: blob_nuevo}`). Cada blob debe caber en
    el hueco original (se rellena con ceros si es menor; se recorta si es mayor). Offsets/índice
    intactos → el juego lo lee igual. Sin cambios ⇒ idéntico."""
    if not replacements:
        return data
    out = bytearray(data)
    idx = {e.off: e.size for e in entries(data)}
    for off, blob in replacements.items():
        room = idx.get(off)
        if room is None:
            continue
        b = blob[:room] if len(blob) > room else blob + b"\x00" * (room - len(blob))
        out[off:off + room] = b
    return bytes(out)
