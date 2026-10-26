"""Equipación del SIMULADOR de PC Fútbol 5 y 6 — dibujarla y volver a guardarla.

A diferencia de las ediciones FDI (7/2000/2001), donde la equipación es un GIF que se enseña
tal cual, aquí NO hay ninguna imagen: cada equipo tiene 192 bytes en `DATSIM.PKF`
(`P96A<ptr>.DAT` la 1ª, `P96B<ptr>.DAT` la 2ª) que son **índices de la paleta VGA** del juego,
con los que el simulador colorea el sprite del jugador.

Reparto de los 192 bytes:

      0-127   TEXTURA de la camiseta: rejilla de 16 columnas × 8 filas
    128-133   rampa de sombreado del color base (6 tonos, oscuro→claro)
    134-152   detalle y constantes (botas, piel, bordes)
    153-155   PANTALÓN
    156-161   MEDIAS: dos piernas × 3 tonos (rampa, igual que el pantalón)
    162-191   una tercera zona sin identificar

**La rejilla es 16×8 (2026-08-24).** Antes se daba por hecho que los bytes 0-133 eran una tira
por columnas, y así se dibujaba: se veían solo las primeras columnas y el resto se inventaba
repitiéndolas. Los datos lo desmienten — en 400 equipos NINGUNO tiene la tira periódica, y al
imprimir los bytes de 16 en 16 aparece la rejilla a simple vista: el Barcelona repite ocho
filas idénticas de `8c 80 80 8c…` (rayas verticales) y el Madrid las tiene todas a `7f`. Que
128 = 16×8 exacto y que justo después venga una rampa evidente (`7f 7c 7a 77 73 71` en el
Madrid) lo confirma.

Eso permite las dos cosas que se hacen aquí: dibujar la camiseta ENTERA, y **reconstruir los
bytes a partir del dibujo**, porque cada byte tiene su propia celda o franja. Lo que el dibujo
no enseña (la rampa, las constantes y la tercera zona) se conserva del kit original.

El viaje de ida y vuelta —dibujar y volver a leer— devuelve los 192 bytes IDÉNTICOS en las
1.625 equipaciones de 6.0 Oro (813 primeras + 812 segundas), así que descargar y volver a subir
sin tocar nada no cambia el fichero.
"""
from __future__ import annotations

import io

KIT_LEN = 192
COLS, FILAS = 16, 8
REJILLA = COLS * FILAS            # 128 bytes de textura de camiseta
RAMPA = slice(128, 134)
PANTALON = 153
MEDIAS = 156

# --- Cómo se dibuja (mismo mapa para pintar y para volver a leer) --------------------------
CELDA = 8                          # lado en píxeles de cada celda de la rejilla
MARGEN = 8
_ANCHO = COLS * CELDA + MARGEN * 2                 # 144
_CAM_Y = MARGEN
_PANT_Y = _CAM_Y + FILAS * CELDA + 6
_PANT_H = 26
_MED_Y = _PANT_Y + _PANT_H + 4
_MED_H = 22
_ALTO = _MED_Y + _MED_H + MARGEN
_FONDO = (24, 25, 30)

# pantalón y medias: cada byte en su franja, para poder recuperarlos del dibujo
_PANT_X = (MARGEN, _ANCHO - MARGEN)
_PIERNAS = ((MARGEN + 10, MARGEN + 44), (_ANCHO - MARGEN - 44, _ANCHO - MARGEN - 10))

TAM = (_ANCHO, _ALTO)


def palette_from_bmp(bmp: bytes) -> list[tuple[int, int, int]]:
    """Paleta VGA (256 colores RGB) de un BMP de 8 bits del propio juego.

    Cualquier BMP256 de `DATSIM.PKF` vale (se usa `NUMCAM.BMP`): todos comparten la paleta del
    simulador. Va en la cabecera, a partir del byte 54, en BGRA."""
    if len(bmp) < 54 + 256 * 4:
        raise ValueError("BMP demasiado corto para llevar una paleta de 256")
    return [(bmp[54 + i * 4 + 2], bmp[54 + i * 4 + 1], bmp[54 + i * 4]) for i in range(256)]


def render_png(kit: bytes, palette) -> bytes:
    """PNG de la equipación: la camiseta entera (16×8), el pantalón y las medias."""
    from PIL import Image, ImageDraw

    if len(kit) < KIT_LEN:
        raise ValueError(f"una equipación son {KIT_LEN} bytes, no {len(kit)}")
    im = Image.new("RGB", TAM, _FONDO)
    d = ImageDraw.Draw(im)

    for f in range(FILAS):
        for c in range(COLS):
            x, y = MARGEN + c * CELDA, _CAM_Y + f * CELDA
            d.rectangle([x, y, x + CELDA - 1, y + CELDA - 1],
                        fill=palette[kit[f * COLS + c]])

    x0, x1 = _PANT_X
    ancho = (x1 - x0) / 3
    for i in range(3):                                     # los 3 bytes del pantalón
        d.rectangle([round(x0 + i * ancho), _PANT_Y, round(x0 + (i + 1) * ancho) - 1,
                     _PANT_Y + _PANT_H - 1], fill=palette[kit[PANTALON + i]])

    # Cada media son TRES bytes, como el pantalón: no es "color + vuelta" sino una rampa de
    # tonos (el ptr 3 lleva `7a 73 73` y el 12 `81 7c 7c`). Se pinta cada uno en su franja, que
    # es lo que permite recuperarlos luego del dibujo.
    for i, (a, b) in enumerate(_PIERNAS):
        franja = (b - a) / 3
        for j in range(3):
            d.rectangle([round(a + j * franja), _MED_Y, round(a + (j + 1) * franja) - 1,
                         _MED_Y + _MED_H - 1], fill=palette[kit[MEDIAS + i * 3 + j]])

    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _indice(rgb, palette) -> int:
    """El color de la paleta del juego más parecido. Si el PNG viene tal cual se descargó, el
    color ES uno de la paleta y acierta exacto; si el usuario ha pintado encima con otro tono,
    se queda con el más cercano, que es todo lo que se puede hacer con una paleta fija."""
    r, g, b = rgb[:3]
    mejor, dist = 0, None
    for i, (pr, pg, pb) in enumerate(palette):
        dd = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dist is None or dd < dist:
            mejor, dist = i, dd
            if dd == 0:
                break
    return mejor


def png_to_kit(png: bytes, base: bytes, palette) -> bytes:
    """Reconstruye los 192 bytes a partir de un PNG dibujado por `render_png`.

    `base` es la equipación de la que se parte: los bytes que el dibujo NO enseña —la rampa de
    sombreado, las constantes y la tercera zona— se conservan de ella en vez de inventarlos.
    Si la imagen viene con otro tamaño se reescala al canónico, así que vale con respetar la
    composición aunque se edite a mayor resolución."""
    from PIL import Image

    if len(base) < KIT_LEN:
        raise ValueError(f"la equipación de partida son {KIT_LEN} bytes, no {len(base)}")
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.size != TAM:
        im = im.resize(TAM, Image.NEAREST)
    out = bytearray(base[:KIT_LEN])

    for f in range(FILAS):
        for c in range(COLS):
            px = im.getpixel((MARGEN + c * CELDA + CELDA // 2, _CAM_Y + f * CELDA + CELDA // 2))
            out[f * COLS + c] = _indice(px, palette)

    x0, x1 = _PANT_X
    ancho = (x1 - x0) / 3
    for i in range(3):
        px = im.getpixel((round(x0 + (i + 0.5) * ancho), _PANT_Y + _PANT_H // 2))
        out[PANTALON + i] = _indice(px, palette)

    for i, (a, b) in enumerate(_PIERNAS):
        franja = (b - a) / 3
        for j in range(3):
            px = im.getpixel((round(a + (j + 0.5) * franja), _MED_Y + _MED_H // 2))
            out[MEDIAS + i * 3 + j] = _indice(px, palette)
    return bytes(out)
