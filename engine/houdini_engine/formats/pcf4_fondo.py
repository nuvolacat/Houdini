"""Fondos de pantalla por TILES de PCF 4.0/4.5 (`GRAFICOS/FON_*.BLO` + `MAP_*.BIN`).

Ingeniería inversa confirmada con FUTBOL_RELOAD (creador de la comunidad):

- **Paleta**: `GRAFICOS/PALETA.BBM` — IFF (chunk `CMAP`, tamaños big-endian), 256 RGB.
- **`.BLO`** (tileset): tiles de 16×16 px, 256 bytes cada uno, sin cabecera, en formato
  planar **Mode-X**: el píxel (x,y) del tile = `blo[base + (x%4)*64 + y*4 + (x//4)]`,
  con `base = idx*256`.
- **`.BIN`** (mapa): 128×48 = 6144 entradas u16 LE. bits 0-14 = índice de tile;
  bit 15 = espejo horizontal. Render → imagen de 2048×768.
"""
from __future__ import annotations

from PIL import Image

TILE = 16
MAP_W = 128
MAP_H = 48
IMG_W = MAP_W * TILE            # 2048
IMG_H = MAP_H * TILE            # 768


def read_bbm_palette(data: bytes) -> list[tuple[int, int, int]]:
    """Lee la paleta de un `PALETA.BBM` (IFF, chunk CMAP). 256 colores."""
    pal: list[tuple[int, int, int]] = []
    pos = 12
    n = len(data)
    while pos + 8 <= n:
        cid = data[pos:pos + 4]
        tam = int.from_bytes(data[pos + 4:pos + 8], "big")
        if cid == b"CMAP":
            cnt = min(256, tam // 3)
            for i in range(cnt):
                o = pos + 8 + i * 3
                pal.append((data[o], data[o + 1], data[o + 2]))
            break
        pos += 8 + tam + (tam % 2)
    while len(pal) < 256:
        pal.append((0, 0, 0))
    return pal


def decode(blo: bytes, mapa: bytes, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Monta el fondo (2048×768) a partir del tileset, el mapa y la paleta."""
    buf = bytearray(IMG_W * IMG_H)
    for ty in range(MAP_H):
        for tx in range(MAP_W):
            k = ty * MAP_W + tx
            e = mapa[k * 2] | (mapa[k * 2 + 1] << 8)
            idx = e & 0x7FFF
            espejo = (e & 0x8000) != 0
            base = idx * 256
            if base + 256 > len(blo):
                continue
            ox, oy = tx * TILE, ty * TILE
            for plano in range(4):
                for y in range(TILE):
                    row = (oy + y) * IMG_W + ox
                    b = base + plano * 64 + y * 4
                    for xb in range(4):
                        x = xb * 4 + plano
                        if espejo:
                            x = TILE - 1 - x
                        buf[row + x] = blo[b + xb]
    img = Image.frombytes("P", (IMG_W, IMG_H), bytes(buf))
    flat: list[int] = []
    for r, g, b in palette:
        flat += [r, g, b]
    img.putpalette(flat)
    return img.convert("RGB")


def content_bbox(img: Image.Image, thr: float = 0.06) -> tuple[int, int, int, int]:
    """Rectángulo (x0,y0,x1,y1) del CONTENIDO real, descartando el relleno de fondo del
    lienzo 2048×768 (el juego solo muestra esta zona). Alineado a tiles de 16.
    Fondo = color de la esquina inferior-derecha; se descartan filas/columnas casi vacías."""
    px = img.load()
    w, h = img.size
    bg = px[w - 1, h - 1]

    def isbg(c: tuple) -> bool:
        return abs(c[0] - bg[0]) < 10 and abs(c[1] - bg[1]) < 10 and abs(c[2] - bg[2]) < 10

    ys_s = range(0, h, 3)
    xs_s = range(0, w, 3)
    col = [sum(0 if isbg(px[x, y]) else 1 for y in ys_s) for x in range(w)]
    row = [sum(0 if isbg(px[x, y]) else 1 for x in xs_s) for y in range(h)]
    ch, cw = len(ys_s), len(xs_s)
    xs = [x for x in range(w) if col[x] > thr * ch]
    ys = [y for y in range(h) if row[y] > thr * cw]
    if not xs or not ys:
        return (0, 0, w, h)
    x0 = (min(xs) // TILE) * TILE
    y0 = (min(ys) // TILE) * TILE
    x1 = min(w, ((max(xs) // TILE) + 1) * TILE)
    y1 = min(h, ((max(ys) // TILE) + 1) * TILE)
    return (x0, y0, x1, y1)


def _nearest(pal: list[tuple[int, int, int]], rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best, bi = 1 << 30, 1
    for i in range(1, len(pal)):       # 0 = fondo/transparente, se evita salvo forzado
        pr, pg, pb = pal[i]
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if d < best:
            best, bi = d, i
            if d == 0:
                break
    return bi


def _tile_to_planar(idx_rows: list[list[int]]) -> bytes:
    """256 bytes planar Mode-X de un tile 16×16 dado por índices."""
    t = bytearray(256)
    for plano in range(4):
        for y in range(TILE):
            b = plano * 64 + y * 4
            for xb in range(4):
                x = xb * 4 + plano
                t[b + xb] = idx_rows[y][x]
    return bytes(t)


def encode(source_png: bytes, palette: list[tuple[int, int, int]],
           max_tiles: int = 32000) -> tuple[bytes, bytes]:
    """Reconstruye (`.BLO`, `.BIN`) desde una imagen: la escala a 2048×768, la trocea en
    tiles 16×16 y reaprovecha tiles repetidos y espejados (como el original). Devuelve
    (tileset, mapa). Si se pasa de `max_tiles`, aún así funciona (solo crece el .BLO)."""
    import io
    src = Image.open(io.BytesIO(source_png)).convert("RGB").resize((IMG_W, IMG_H), Image.LANCZOS)
    sp = src.load()

    tiles: list[bytes] = []
    index: dict[bytes, int] = {}
    mapa = bytearray(MAP_W * MAP_H * 2)
    cache: dict[tuple[int, int, int], int] = {}     # rgb → índice (acelera el matching)

    def near(rgb: tuple[int, int, int]) -> int:
        i = cache.get(rgb)
        if i is None:
            i = _nearest(palette, rgb)
            cache[rgb] = i
        return i

    for ty in range(MAP_H):
        for tx in range(MAP_W):
            ox, oy = tx * TILE, ty * TILE
            rows = [[near(sp[ox + x, oy + y]) for x in range(TILE)]
                    for y in range(TILE)]
            normal = _tile_to_planar(rows)
            mir_rows = [[rows[y][TILE - 1 - x] for x in range(TILE)] for y in range(TILE)]
            mirror = _tile_to_planar(mir_rows)
            # reutilizar tile existente (normal o espejo)
            if normal in index:
                ent = index[normal]
            elif mirror in index:
                ent = index[mirror] | 0x8000
            else:
                ti = len(tiles)
                tiles.append(normal)
                index[normal] = ti
                ent = ti
            k = ty * MAP_W + tx
            mapa[k * 2] = ent & 0xFF
            mapa[k * 2 + 1] = (ent >> 8) & 0xFF
    return b"".join(tiles), bytes(mapa)
