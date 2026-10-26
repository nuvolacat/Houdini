"""Sprites de ANIMACIÓN de PCF 4.0/4.5 — `GRAFICOS/*.EMP` (155 ficheros, 5100+ frames).

Son las animaciones del simulador (andar, chutar, tarjetas, balón…). Distinto del `.EMP`
del ESCUDO del simulador (ese es `ESCUDOS/*.EMP`, tamaño fijo; ver `pcf4_emp.py`).

Ingeniería inversa confirmada con FUTBOL_RELOAD:
- Cabecera 16 bytes; `data[1]==0x41` → descriptores de **8** bytes, si no de **6**
  (variante antigua). El parser prueba inicios desde 0x10 y elige el recorrido que
  consume el fichero.
- Cada frame: descriptor `X(u16)=bytesPorFila+1, alto(u16), tamPlano(u16)[, 0(u16)]` y
  luego **4 planos Mode-X** de `tamPlano` bytes. `ancho = bytesPorFila*4`,
  `tamPlano = bytesPorFila*alto`. Píxel(x,y) = `data[datos + (x%4)*tamPlano + y*bytesPorFila + x//4]`.
  **Índice 0 = transparente.**
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass
class Frame:
    offset: int
    datos: int
    ancho: int
    alto: int
    bpr: int          # bytes por fila (= ancho/4)
    tam_plano: int


def _u16(d: bytes, o: int) -> int:
    return d[o] | (d[o + 1] << 8)


def _read_desc(d: bytes, off: int, tdesc: int) -> Frame | None:
    if off + tdesc > len(d):
        return None
    x = _u16(d, off)
    h = _u16(d, off + 2)
    ps = _u16(d, off + 4)
    if tdesc == 8 and _u16(d, off + 6) != 0:
        return None
    if h < 1 or h > 256 or x < 2 or ps < 1:
        return None
    bpr = x - 1
    if bpr * h != ps:
        return None
    ancho = bpr * 4
    if ancho > 340:
        return None
    if off + tdesc + 4 * ps > len(d):
        return None
    return Frame(off, off + tdesc, ancho, h, bpr, ps)


def _walk(d: bytes, inicio: int, tdesc: int) -> tuple[list[Frame], int]:
    frames: list[Frame] = []
    off = inicio
    while off + 8 <= len(d):
        f = _read_desc(d, off, tdesc)
        if f is None:
            found = None
            for salto in range(2, 17, 2):        # relleno de alineación entre frames
                f = _read_desc(d, off + salto, tdesc)
                if f is not None:
                    found = f
                    break
            if found is None:
                break
            f = found
        frames.append(f)
        off = f.datos + 4 * f.tam_plano
    return frames, off


def parse_frames(d: bytes) -> list[Frame]:
    if len(d) < 20:
        return []
    tdesc = 8 if d[1] == 0x41 else 6
    limite = min(len(d), 0x600)
    best: list[Frame] = []
    for ini in range(0x10, limite, 2):
        fr, fin = _walk(d, ini, tdesc)
        if fr and (len(d) - fin) < 24 and len(fr) > len(best):
            best = fr
    return best


def decode_frame(d: bytes, f: Frame, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Frame → imagen RGBA (índice 0 transparente)."""
    img = Image.new("RGBA", (f.ancho, f.alto), (0, 0, 0, 0))
    px = img.load()
    for plano in range(4):
        base = f.datos + plano * f.tam_plano
        for y in range(f.alto):
            row = base + y * f.bpr
            for xb in range(f.bpr):
                idx = d[row + xb]
                if idx == 0:
                    continue
                x = xb * 4 + plano
                if x < f.ancho:
                    r, g, b = palette[idx]
                    px[x, y] = (r, g, b, 255)
    return img


def _nearest(pal: list[tuple[int, int, int]], rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    best, bi = 1 << 30, 1
    for i in range(1, len(pal)):        # 0 = transparente, se reserva
        pr, pg, pb = pal[i]
        dd = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dd < best:
            best, bi = dd, i
            if dd == 0:
                break
    return bi


def encode_frame(d: bytearray, f: Frame, png: bytes,
                 palette: list[tuple[int, int, int]]) -> None:
    """Reescribe (in-place) los píxeles del frame con `png` (escalado a su tamaño exacto).
    Alfa < 128 → índice 0 (transparente). Conserva el tamaño → offsets intactos."""
    import io
    src = Image.open(io.BytesIO(png)).convert("RGBA").resize((f.ancho, f.alto), Image.LANCZOS)
    sp = src.load()
    cache: dict = {}
    for plano in range(4):
        base = f.datos + plano * f.tam_plano
        for y in range(f.alto):
            row = base + y * f.bpr
            for xb in range(f.bpr):
                x = xb * 4 + plano
                if x >= f.ancho:
                    d[row + xb] = 0
                    continue
                r, g, b, a = sp[x, y]
                if a < 128:
                    d[row + xb] = 0
                else:
                    key = (r, g, b)
                    idx = cache.get(key)
                    if idx is None:
                        idx = _nearest(palette, key)
                        cache[key] = idx
                    d[row + xb] = idx
