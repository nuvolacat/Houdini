"""Códec de imágenes de PCF 4.0/4.5 (ficheros .DFG / .EMP).

Tres familias (ref: FUTBOL_RELOAD/transform_minifoto.cpp + pruebas/):
1. **Bitplane con paleta FIJA** (MINIESC, MINIFOTO, CAMISAS): cabecera de 8 bytes
   `[01][W][00][H][00][planos][00][00]`, datos por filas (planos × ⌈W/8⌉ bytes:
   plano a,b,c,d), índice de color = bit(a)<<0|bit(b)<<1|bit(c)<<2|bit(d)<<3
   (MSB primero), terminado en 0xFF. Paleta según el tipo.
2. **Bitplane con paleta EN FICHERO** (BIGESC, BIGFOTO): cabecera `00 10 00 00`
   (u16 W, u16 H) + paleta 16×RGB + 8 bytes + datos bitplane.
3. **256 colores intercalado** (ESCUDOS/*.EMP = escudo del simulador): cabecera
   0x18 bytes + datos 1 byte/píxel, columnas intercaladas de 4 en 4 (4 pasadas de
   columnas: 0,4,8… luego 1,5,9…). Dims 52×65 (grande, size>1500) o 32×45. Paleta
   PROPIA de 256 colores (`refdata/pcf4_palette_sim.json`), NO la VGA — verificado
   en FUTBOL_RELOAD (`paleta_escudos_sim`/`fotosim2QImage`). AÚN NO implementado
   (ni decode ni encode): el simulador seguiría con los escudos originales.

Todas las funciones de decode devuelven (rgb_bytes, W, H) — RGB 3 bytes/píxel.
"""
from __future__ import annotations

import struct

# Paletas de 16 colores (0xRRGGBB), de transform_minifoto.cpp
PALETA_MINIFOTO = [
    0x000000, 0x186D14, 0x86AA1C, 0xA6B6CB, 0xF7DB18, 0x0010E3, 0xF70000, 0x618EB6,
    0x592400, 0x9A6124, 0xDB9224, 0xFFD786, 0x696969, 0x9A9A9A, 0xC7C7C7, 0xF7F7F7,
]
PALETA_MINIESC = [
    0x000000, 0x186D14, 0x86AA1C, 0xAEBED3, 0xFFE320, 0x0000FF, 0xEF2000, 0x6996BE,
    0x6DA6AA, 0x004975, 0xA2D324, 0x005961, 0x717171, 0xA2A2A2, 0xCFCFCF, 0xFFFFFF,
]


def _rgb(pal: list[int], idx: int) -> bytes:
    c = pal[idx & 0x0F]
    return bytes([(c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF])


def decode_bitplane_fixed(data: bytes, pal: list[int]) -> tuple[bytes, int, int]:
    """Familia 1: cabecera 8 bytes con W/H/planos + datos bitplane + 0xFF."""
    w, h, planes = data[1], data[3], data[5]
    if not (0 < w <= 256 and 0 < h <= 256 and planes == 4):
        raise ValueError(f"cabecera .DFG inesperada: {data[:8].hex()}")
    bpr = (w + 7) // 8            # bytes por fila y plano
    out = bytearray(w * h * 3)
    pos = 8
    for y in range(h):
        planos = [data[pos + p * bpr: pos + (p + 1) * bpr] for p in range(4)]
        pos += 4 * bpr
        for bx in range(bpr):
            for i in range(8):
                x = bx * 8 + (7 - i)
                if x >= w:
                    continue
                idx = (((planos[0][bx] >> i) & 1)
                       | (((planos[1][bx] >> i) & 1) << 1)
                       | (((planos[2][bx] >> i) & 1) << 2)
                       | (((planos[3][bx] >> i) & 1) << 3))
                out[(y * w + x) * 3: (y * w + x) * 3 + 3] = _rgb(pal, idx)
    return bytes(out), w, h


def decode_bitplane_palfile(data: bytes, w: int = 0, h: int = 0) -> tuple[bytes, int, int]:
    """Familia 2 (BIGFOTO, paleta EN fichero): 2 bytes marcador + paleta 16×RGB +
    cabecera de dims [01][W][00][H][00][04][00][00] + datos bitplane (4 planos) + FF.
    Las dimensiones REALES van en la cabecera (BIGFOTO = 124×182)."""
    pos = 2
    pal = []
    for _ in range(16):
        pal.append((data[pos] << 16) | (data[pos + 1] << 8) | data[pos + 2])
        pos += 3
    # cabecera de dimensiones (8 bytes) — la W/H reales mandan sobre los params
    w = data[pos + 1] or w
    h = data[pos + 3] or h
    pos += 8
    bpr = (w + 7) // 8
    out = bytearray(w * h * 3)
    for y in range(h):
        planos = [data[pos + p * bpr: pos + (p + 1) * bpr] for p in range(4)]
        pos += 4 * bpr
        for bx in range(bpr):
            for i in range(8):
                x = bx * 8 + (7 - i)
                if x >= w:
                    continue
                idx = (((planos[0][bx] >> i) & 1)
                       | (((planos[1][bx] >> i) & 1) << 1)
                       | (((planos[2][bx] >> i) & 1) << 2)
                       | (((planos[3][bx] >> i) & 1) << 3))
                out[(y * w + x) * 3: (y * w + x) * 3 + 3] = _rgb(pal, idx)
    return bytes(out), w, h


def decode_bigfoto(data: bytes) -> tuple[bytes, int, int]:
    """Foto grande de jugador: 124×182, paleta en fichero."""
    return decode_bitplane_palfile(data, 124, 182)


BIGFOTO_W, BIGFOTO_H = 124, 182


def _quantize16(im, dither):
    """Cuantiza una imagen RGB a ≤16 colores con paleta ADAPTATIVA. Usa **libimagequant**
    (el algoritmo de `pngquant`, calidad muy superior a MEDIANCUT) si Pillow lo trae compilado;
    si no, cae a MEDIANCUT. `dither` = Image.FLOYDSTEINBERG (fotos) o Image.NONE (gráficos planos:
    escudos → sin dither para no meter confeti)."""
    from PIL import Image, features
    if features.check("libimagequant"):
        try:
            return im.quantize(colors=16, method=Image.LIBIMAGEQUANT,
                               dither=1 if dither != Image.NONE else 0)
        except Exception:  # noqa: BLE001
            pass
    return im.quantize(colors=16, method=Image.MEDIANCUT, dither=dither)


def encode_bigfoto(png_bytes: bytes) -> bytes:
    """PNG → BIGFOTO .DFG (124×182, paleta EN fichero de 16 colores ADAPTATIVA).
    Formato: [00 10] + paleta 16×RGB + [01][124][00][182][00][04][00][00] + planos + FF."""
    import io
    from PIL import Image, ImageOps
    w, h = BIGFOTO_W, BIGFOTO_H
    # FOTO: conservar aspecto (recorte "cover" centrado en la cara) en vez de estirar.
    from .image import encuadre_ficha
    im = encuadre_ficha(Image.open(io.BytesIO(png_bytes)), (w, h))
    q = _quantize16(im, Image.FLOYDSTEINBERG)
    pal = q.getpalette()[:48]                       # 16 colores × RGB
    pal += [0] * (48 - len(pal))
    idx = q.load()
    out = bytearray([0x00, 0x10])                   # marcador
    out += bytes(pal)                               # paleta 16×RGB
    out += bytes([0x01, w & 0xFF, 0x00, h & 0xFF, 0x00, 0x04, 0x00, 0x00])  # cabecera dims
    bpr = (w + 7) // 8
    for y in range(h):
        planes = [bytearray(bpr) for _ in range(4)]
        for x in range(w):
            v = idx[x, y] & 0x0F
            bit = 7 - (x % 8)
            b = x // 8
            for p in range(4):
                if (v >> p) & 1:
                    planes[p][b] |= 1 << bit
        for p in range(4):
            out += planes[p]
    out.append(0xFF)
    return bytes(out)


def encode_palfile_exact(png_bytes: bytes, w: int, h: int,
                         bg: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    """PNG → imagen palfile (marcador 00 10 + paleta 16×RGB + cabecera dims + bitplane + FF)
    a dimensiones EXACTAS w×h (W/H como u16 LE en la cabecera). Compone el transparente
    sobre `bg`. Se usa para reemplazar sprites de tamaño fijo
    manteniendo el MISMO número de bytes → sustitución drop-in sin descuadrar el fichero."""
    import io
    from PIL import Image
    src = Image.open(io.BytesIO(png_bytes))
    if src.mode in ("RGBA", "LA", "PA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA")
        canvas = Image.new("RGBA", src.size, (*bg, 255))
        src = Image.alpha_composite(canvas, src).convert("RGB")
    else:
        src = src.convert("RGB")
    if src.size != (w, h):
        src = src.resize((w, h), Image.LANCZOS)
    q = src.quantize(colors=16, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = q.getpalette()[:48]
    pal += [0] * (48 - len(pal))
    idx = q.load()
    out = bytearray([0x00, 0x10])
    out += bytes(pal)
    out += bytes([0x01, w & 0xFF, (w >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF, 0x04, 0x00, 0x00])
    bpr = (w + 7) // 8
    for y in range(h):
        planes = [bytearray(bpr) for _ in range(4)]
        for x in range(w):
            v = idx[x, y] & 0x0F
            bit = 7 - (x % 8)
            b = x // 8
            for p in range(4):
                if (v >> p) & 1:
                    planes[p][b] |= 1 << bit
        for p in range(4):
            out += planes[p]
    out.append(0xFF)
    return bytes(out)


def encode_palfile_with_palette(png_bytes: bytes, w: int, h: int, pal48: bytes,
                                bg: tuple[int, int, int] = (255, 255, 255),
                                allow: list[int] | None = None) -> bytes:
    """Como encode_palfile_exact pero cuantiza a una PALETA DADA (16 colores = 48 bytes) y la
    escribe VERBATIM en el fichero. Necesario para reemplazar sprites de tamaño fijo: el juego
    usa la paleta ORIGINAL del sprite (no la que metas), así que hay que quedarse con ella y
    mapear los píxeles a esos 16 colores; si no, salen colores basura y fondo negro.

    `allow` = subconjunto de índices de la paleta a los que se puede mapear (para evitar que
    un dorado con degradado caiga en el verde/azul de la paleta). Mapeo manual al más cercano.
    """
    import io
    from PIL import Image
    src = Image.open(io.BytesIO(png_bytes))
    if src.mode in ("RGBA", "LA", "PA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA")
        canvas = Image.new("RGBA", src.size, (*bg, 255))
        src = Image.alpha_composite(canvas, src).convert("RGB")
    else:
        src = src.convert("RGB")
    if src.size != (w, h):
        src = src.resize((w, h), Image.LANCZOS)
    pal = [(pal48[3 * i], pal48[3 * i + 1], pal48[3 * i + 2]) for i in range(16)]
    idxs = allow if allow else list(range(16))
    px = src.load()

    def nearest(c: tuple) -> int:
        return min(idxs, key=lambda i: (c[0] - pal[i][0]) ** 2
                   + (c[1] - pal[i][1]) ** 2 + (c[2] - pal[i][2]) ** 2)

    out = bytearray([0x00, 0x10]) + bytes(pal48[:48])
    out += bytes([0x01, w & 0xFF, (w >> 8) & 0xFF, h & 0xFF, (h >> 8) & 0xFF, 0x04, 0x00, 0x00])
    bpr = (w + 7) // 8
    for y in range(h):
        planes = [bytearray(bpr) for _ in range(4)]
        for x in range(w):
            v = nearest(px[x, y]) & 0x0F
            bit = 7 - (x % 8)
            b = x // 8
            for p in range(4):
                if (v >> p) & 1:
                    planes[p][b] |= 1 << bit
        for p in range(4):
            out += planes[p]
    out.append(0xFF)
    return bytes(out)


def decode_stadium(data: bytes) -> tuple[bytes, int, int]:
    """Foto de estadio (BIGCAMP/ES95NNNN.DFG, familia B con paleta en fichero). Dims en cabecera."""
    return decode_bitplane_palfile(data)


def encode_stadium(original_dfg: bytes, png_bytes: bytes) -> bytes:
    """Reemplaza una foto de estadio (BIGCAMP .DFG) por otra, conservando las dimensiones EXACTAS
    del original (el juego las lee de la cabecera). Genera una paleta óptima de 16 colores para la
    foto nueva (mediancut) — como el juego una foto, no un escudo plano."""
    pos = 2 + 48                                    # marcador 00 10 + paleta 16×RGB
    w = original_dfg[pos + 1] | (original_dfg[pos + 2] << 8)
    h = original_dfg[pos + 3] | (original_dfg[pos + 4] << 8)
    if not (0 < w <= 4096 and 0 < h <= 4096):
        raise ValueError("cabecera BIGCAMP no válida")
    return encode_palfile_exact(png_bytes, w, h)


def encode_bigesc(png_bytes: bytes, max_w: int = 130, max_h: int = 178,
                  bg: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    """PNG → BIGESC .DFG (escudo GRANDE, paleta EN fichero, mismo formato que BIGFOTO).
    Las dims son VARIABLES por equipo (el juego las lee de la cabecera del fichero), así
    que se preserva el ASPECTO del escudo dentro de una caja `max_w`×`max_h` — sin
    deformar. El fondo transparente se compone sobre `bg` (BLANCO: en la ficha/alineación
    el escudo va sobre recuadro blanco)."""
    import io
    from PIL import Image
    src = Image.open(io.BytesIO(png_bytes))
    if src.mode in ("RGBA", "LA", "PA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA")
        # borde DURO de transparencia (umbral de alpha) → sin halo gris del anti-aliasing
        r, g, b, a = src.split()
        mask = a.point(lambda v: 255 if v >= 128 else 0)
        canvas = Image.new("RGB", src.size, bg)
        canvas.paste(Image.merge("RGB", (r, g, b)), (0, 0), mask)
        src = canvas
    else:
        src = src.convert("RGB")
    sw, sh = src.size
    if min(sw, sh) >= 48:                            # mediana suave: quita ruido/JPEG (menos puntitos)
        from PIL import ImageFilter
        src = src.filter(ImageFilter.MedianFilter(3))
    scale = min(max_w / sw, max_h / sh)
    w = max(1, min(max_w, round(sw * scale)))
    h = max(1, min(max_h, round(sh * scale)))
    im = src.resize((w, h), Image.LANCZOS)
    from PIL import ImageEnhance
    im = ImageEnhance.Color(im).enhance(1.4)          # colores más vivos
    # SIN dither: el escudo grande es un gráfico plano; el Floyd-Steinberg lo llena de
    # confeti de colores (feo en juego). El dither solo se deja en fotos (encode_bigfoto).
    # Paleta óptima con libimagequant si está (mejor que MEDIANCUT para los 16 colores).
    q = _quantize16(im, Image.NONE)
    pal = q.getpalette()[:48]
    pal += [0] * (48 - len(pal))
    idx = q.load()
    out = bytearray([0x00, 0x10])                   # marcador
    out += bytes(pal)                               # paleta 16×RGB
    out += bytes([0x01, w & 0xFF, 0x00, h & 0xFF, 0x00, 0x04, 0x00, 0x00])  # cabecera dims
    bpr = (w + 7) // 8
    for y in range(h):
        planes = [bytearray(bpr) for _ in range(4)]
        for x in range(w):
            v = idx[x, y] & 0x0F
            bit = 7 - (x % 8)
            b = x // 8
            for p in range(4):
                if (v >> p) & 1:
                    planes[p][b] |= 1 << bit
        for p in range(4):
            out += planes[p]
    out.append(0xFF)
    return bytes(out)


def encode_bitplane_fixed(png_bytes: bytes, pal: list[int], w: int, h: int,
                          bg: tuple[int, int, int] = (255, 255, 255),
                          keep_aspect: bool = False, saturate: float = 1.0) -> bytes:
    """PNG → .DFG bitplane con paleta FIJA (para subir escudo/camiseta). Cuantiza a
    los 16 colores de la paleta, cabecera [01][W][00][H][00][04][00][00] + datos + FF.
    El fondo TRANSPARENTE se compone sobre `bg` (BLANCO para escudos=idx15; GRIS
    0x9a9a9a para camisetas=idx13, que casa con el fondo gris del juego). En RGB directo
    el fondo saldría NEGRO. `keep_aspect` (escudos): encaja centrado SIN deformar."""
    import io
    from PIL import Image, ImageOps
    src = Image.open(io.BytesIO(png_bytes))
    has_alpha = (src.mode in ("RGBA", "LA", "PA")
                 or (src.mode == "P" and "transparency" in src.info))
    src = src.convert("RGBA") if has_alpha else src.convert("RGB").convert("RGBA")
    # ASPECTO: escudos = encajar centrado sin deformar; camisetas/minifoto = estirar
    fitted = (ImageOps.contain(src, (w, h), Image.LANCZOS) if keep_aspect
              else src.resize((w, h), Image.LANCZOS))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
    # borde DURO de transparencia (umbral de alpha) → sin halo gris; el fondo va a `bg`
    r, g, b, a = canvas.split()
    mask = a.point(lambda v: 255 if v >= 128 else 0)
    im = Image.new("RGB", (w, h), bg)
    im.paste(Image.merge("RGB", (r, g, b)), (0, 0), mask)
    if not keep_aspect and min(im.size) >= 48:        # mediana anti-puntitos (no en escudos: crispa)
        from PIL import ImageFilter
        im = im.filter(ImageFilter.MedianFilter(3))
    if saturate != 1.0:                               # colores más VIVOS → saltan a la paleta viva
        from PIL import ImageEnhance
        im = ImageEnhance.Color(im).enhance(saturate)
    # paleta PIL de 16 colores
    palimg = Image.new("P", (1, 1))
    flat = []
    for c in pal:
        flat += [(c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF]
    flat += [0] * (768 - len(flat))
    palimg.putpalette(flat)
    # SIN dither: escudos y camisetas son gráficos planos de pocos colores; el
    # Floyd-Steinberg los llena de puntitos de colores (se ven mal en el juego). El
    # mapeo a color más cercano da líneas limpias.
    q = im.quantize(palette=palimg, dither=Image.NONE)
    idx = q.load()
    out = bytearray([0x01, w & 0xFF, 0x00, h & 0xFF, 0x00, 0x04, 0x00, 0x00])
    bpr = (w + 7) // 8
    for y in range(h):
        planes = [bytearray(bpr) for _ in range(4)]
        for x in range(w):
            v = idx[x, y] & 0x0F
            bit = 7 - (x % 8)
            b = x // 8
            for p in range(4):
                if (v >> p) & 1:
                    planes[p][b] |= 1 << bit
        for p in range(4):
            out += planes[p]
    out.append(0xFF)
    return bytes(out)


def to_png(rgb: bytes, w: int, h: int, transparent_bg: bool = False) -> bytes:
    """RGB crudo → PNG. Si transparent_bg, el color del fondo (el de las esquinas,
    blanco en los escudos de PCF4) se hace transparente por relleno desde los bordes
    — así no se rompen zonas blancas del INTERIOR del dibujo."""
    from PIL import Image
    im = Image.frombytes("RGB", (w, h), rgb)
    if not transparent_bg:
        return _pil_png(im)
    im = im.convert("RGBA")
    px = im.load()
    bg = px[0, 0][:3]
    # BFS desde el borde sobre píxeles del color de fondo → alpha 0
    stack = [(x, y) for x in range(w) for y in (0, h - 1)]
    stack += [(x, y) for y in range(h) for x in (0, w - 1)]
    seen = set()
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        if px[x, y][:3] != bg:
            continue
        px[x, y] = (bg[0], bg[1], bg[2], 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return _pil_png(im)


def _pil_png(im) -> bytes:
    import io
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# Dispatcher por tipo de contenedor
def decode(name: str, data: bytes) -> tuple[bytes, int, int]:
    """name ∈ {MINIESC, MINIFOTO, CAMISAS, BIGESC, BIGFOTO}."""
    name = name.upper()
    if name == "MINIESC":
        return decode_bitplane_fixed(data, PALETA_MINIESC)
    if name in ("MINIFOTO", "CAMISAS"):
        return decode_bitplane_fixed(data, PALETA_MINIFOTO)
    if name == "BIGFOTO":
        return decode_bigfoto(data)
    raise ValueError(f"contenedor de imagen desconocido: {name}")
