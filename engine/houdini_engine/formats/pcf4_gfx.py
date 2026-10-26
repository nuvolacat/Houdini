"""Gráficos de interfaz de PCF 4.0/4.5 — contenedores `GFX*.DAT`.

Contienen los TROFEOS (copas), botones, iconos, marcadores… Formato "Familia A"
(ingeniería inversa confirmada con FUTBOL_RELOAD):

- Paletas VGA de 16 colores embebidas: marcador `00 10 … [+50]=FF`, valores VGA de 6 bits
  expandidos (v==0 o v%4==3), 16 colores RGB desde +2. El fichero no dice qué paleta usa
  cada imagen (lo decide el juego); por defecto la 0.
- Imágenes: cabecera 8B `01, ancho(u16 LE), alto(u16 LE), 04 00 00`; luego los píxeles en
  **4 bitplanes** por fila (16 colores), `rowbytes=(ancho+7)//8`, bit 7 = píxel izquierdo.

Editar mantiene el tamaño (misma geometría) → offsets del contenedor intactos.
"""
from __future__ import annotations

from PIL import Image


def find_palettes(d: bytes) -> list[list[tuple[int, int, int]]]:
    pals: list[list[tuple[int, int, int]]] = []
    o, n = 0, len(d)
    while o + 51 <= n:
        if d[o] == 0x00 and d[o + 1] == 0x10 and d[o + 50] == 0xFF:
            vga = True
            algo = False
            for i in range(2, 50):
                v = d[o + i]
                if v != 0 and v % 4 != 3:
                    vga = False
                    break
                if v != 0:
                    algo = True
            if vga and algo:
                pal = [(d[o + 2 + i * 3], d[o + 3 + i * 3], d[o + 4 + i * 3]) for i in range(16)]
                if pal[0] == (0, 0, 0) and len(set(pal)) >= 10:
                    pals.append(pal)
                    o += 51
                    continue
        o += 1
    return pals


def default_palette_index(filename: str, offset: int, n_palettes: int) -> int:
    """Paleta por defecto de una imagen GFX. El fichero NO indica qué paleta usa cada imagen (lo
    decide el código del juego); por defecto la 0. Excepción portada de FUTBOL_RELOAD: el banner de
    GFX02 ("PC FÚTBOL", logo Dinamic y su zona, offsets 380000-530000) usa la paleta 8 (que es la
    paleta compartida de ese banner ya embebida en el propio GFX02)."""
    fn = filename.upper()
    if not fn.endswith(".DAT"):
        fn += ".DAT"
    if fn == "GFX02.DAT" and 380000 <= offset <= 530000 and n_palettes > 8:
        return 8
    return 0


def index_histogram(d: bytes, off: int, w: int, h: int) -> list[int]:
    """Cuenta de índices de paleta (0-15) usados en la imagen. Es INDEPENDIENTE de la paleta
    (los planos de bits dan el índice; la paleta solo lo colorea) → se calcula UNA vez y sirve
    para puntuar todas las paletas candidatas de forma barata."""
    rb = (w + 7) // 8
    base = off + 8
    hist = [0] * 16
    for y in range(h):
        planes = [base + y * rb * 4 + p * rb for p in range(4)]
        for x in range(w):
            bi = x >> 3
            b = 7 - (x & 7)
            idx = 0
            for p in range(4):
                idx |= ((d[planes[p] + bi] >> b) & 1) << p
            hist[idx] += 1
    return hist


def score_palette(hist: list[int], palette: list[tuple[int, int, int]]) -> float:
    """Puntúa cuánto 'se ve' la imagen con esta paleta. Premia la VARIEDAD de colores distintos
    entre los índices realmente usados (ponderada por su nº de píxeles) + el brillo. Una paleta
    que mapea casi todos los índices usados a negro/oscuro (la típica pal 0 en GFX05/06) puntúa
    bajo; la que los reparte en colores distintos y vivos puntúa alto."""
    pal = list(palette) + [(0, 0, 0)] * (16 - len(palette))
    total = sum(hist) or 1
    seen: set = set()
    score = 0.0
    for idx, cnt in enumerate(hist):
        if not cnt:
            continue
        r, g, b = pal[idx]
        lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255.0
        frac = cnt / total
        key = (r // 24, g // 24, b // 24)          # cuantizado → "colores distintos"
        if key not in seen:
            seen.add(key)
            score += frac * (0.4 + lum)            # variedad de color (ponderada por presencia)
        score += frac * lum * 0.3                  # brillo general (evita paletas casi-negras)
    return score


def best_palette_index(d: bytes, off: int, w: int, h: int,
                       palettes: list[list[tuple[int, int, int]]]) -> int:
    """Índice de la paleta candidata que hace más visible la imagen (auto-mapeo, como el
    `best_palette` de PCF7). Para GFX05/06, que no traen paleta embebida y usan el respaldo
    de GFX01-04, elige una paleta 'no-negra' en vez de la 0 por defecto."""
    if len(palettes) <= 1:
        return 0
    hist = index_histogram(d, off, w, h)
    best_i, best_s = 0, -1.0
    for i, pal in enumerate(palettes):
        s = score_palette(hist, pal)
        if s > best_s:
            best_s, best_i = s, i
    return best_i


def find_images(d: bytes, mn: int = 4, mx: int = 700) -> list[tuple[int, int, int]]:
    """[(offset, ancho, alto)] de las imágenes Familia A del contenedor. Límites mn/mx GENEROSOS:
    el tope antiguo de 320 EXCLUÍA las imágenes GRANDES — el logo grande "PC FUTBOL" del menú
    (640×115, GFX02 idx 176) y la columna VERTICAL de escudos de la Liga + LFP (94×365, idx 229).
    Máximo REAL medido en todo PCF4 GFX = 640 ancho × 365 alto; con 1024 hay margen de sobra para
    verticales/pantallas completas sin cortar ninguna. El guard real contra basura es `need <= n`
    (una imagen no puede declarar más bytes que el fichero); verificado que 700..4000 no añade nada."""
    res = []
    i, n = 0, len(d)
    while i + 8 <= n:
        if d[i] == 0x01 and d[i + 5] == 0x04 and d[i + 6] == 0 and d[i + 7] == 0:
            w = d[i + 1] | (d[i + 2] << 8)
            h = d[i + 3] | (d[i + 4] << 8)
            if mn <= w <= mx and mn <= h <= mx:
                rb = (w + 7) // 8
                need = rb * h * 4
                if i + 8 + need <= n:
                    res.append((i, w, h))
                    i += 8 + need
                    continue
        i += 1
    return res


def decode_image(d: bytes, off: int, w: int, h: int,
                 palette: list[tuple[int, int, int]]) -> Image.Image:
    rb = (w + 7) // 8
    base = off + 8
    img = Image.new("RGB", (w, h))
    px = img.load()
    pal = palette + [(0, 0, 0)] * (16 - len(palette))
    for y in range(h):
        planes = [base + y * rb * 4 + p * rb for p in range(4)]
        for x in range(w):
            bi = x >> 3
            b = 7 - (x & 7)
            idx = 0
            for p in range(4):
                idx |= ((d[planes[p] + bi] >> b) & 1) << p
            px[x, y] = pal[idx]
    return img


def _nearest(pal: list[tuple[int, int, int]], rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best, bi = 1 << 30, 0
    for i in range(len(pal)):
        pr, pg, pb = pal[i]
        dd = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dd < best:
            best, bi = dd, i
            if dd == 0:
                break
    return bi


def encode_image(d: bytearray, off: int, w: int, h: int, png: bytes,
                 palette: list[tuple[int, int, int]]) -> None:
    """Reescribe (in-place) la imagen con `png` (escalado a w×h y cuantizado a los 16
    colores de la paleta). Mantiene el tamaño → el resto del contenedor no se mueve."""
    import io
    src = Image.open(io.BytesIO(png)).convert("RGB").resize((w, h), Image.LANCZOS)
    sp = src.load()
    pal = palette[:16]
    cache: dict = {}
    rb = (w + 7) // 8
    base = off + 8
    # limpiar la región de píxeles
    for k in range(rb * 4 * h):
        d[base + k] = 0
    for y in range(h):
        planes = [base + y * rb * 4 + p * rb for p in range(4)]
        for x in range(w):
            rgb = sp[x, y]
            idx = cache.get(rgb)
            if idx is None:
                idx = _nearest(pal, rgb)
                cache[rgb] = idx
            if idx:
                bi = x >> 3
                b = 7 - (x & 7)
                for p in range(4):
                    if (idx >> p) & 1:
                        d[planes[p] + bi] |= (1 << b)
