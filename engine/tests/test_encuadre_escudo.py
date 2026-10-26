"""Un escudo no se estira: se escala conservando su proporción y se centra.

Dinamic no deformaba. Sus escudos dejan márgenes variables según la forma de cada uno —el
del Zaragoza, estrecho y alto, ocupa 30 px de ancho en un lienzo de 48, con 8 y 10 de
margen— mientras que otros llenan el ancho y dejan margen arriba y abajo. Estirar al tamaño
exacto ensanchaba los escudos estrechos y alargaba los anchos.
"""
from io import BytesIO

import pytest

from houdini_engine.codec import image as IMG
from houdini_engine.codec import pcf7_image as P7I

Image = pytest.importorskip("PIL.Image")

DEST = (48, 64)          # MINIESC


def _png(w, h, color=(210, 0, 0)):
    """Rectángulo de color OPACO que ocupa todo el lienzo, del tamaño pedido."""
    im = Image.new("RGBA", (w, h), color + (255,))
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _caja(bmp):
    """Caja del contenido (lo que no es el índice 0 = fondo transparente)."""
    im = Image.open(BytesIO(bmp))
    px = im.load()
    w, h = im.size
    puntos = [(x, y) for x in range(w) for y in range(h) if px[x, y] != 0]
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("hacer", [
    lambda p: IMG.to_game_bmp(p, DEST, flat=True, encaja=True),
    lambda p: P7I.to_game_bmp(p, DEST, flatten=(0, 0, 0), flat=True, encaja=True),
], ids=["v56", "pcf7"])
def test_un_escudo_ancho_deja_margen_arriba_y_abajo(hacer):
    x0, y0, x1, y1 = _caja(hacer(_png(200, 100)))       # 2:1, más ancho que el lienzo
    assert x1 - x0 + 1 == DEST[0], "debería llenar el ancho"
    assert y1 - y0 + 1 < DEST[1], "no debería llegar a llenar el alto"
    assert abs(y0 - (DEST[1] - 1 - y1)) <= 1, "debería quedar centrado en vertical"


@pytest.mark.parametrize("hacer", [
    lambda p: IMG.to_game_bmp(p, DEST, flat=True, encaja=True),
    lambda p: P7I.to_game_bmp(p, DEST, flatten=(0, 0, 0), flat=True, encaja=True),
], ids=["v56", "pcf7"])
def test_un_escudo_estrecho_deja_margen_a_los_lados(hacer):
    """El caso del Zaragoza: estrecho y alto, no se puede ensanchar."""
    x0, y0, x1, y1 = _caja(hacer(_png(100, 400)))       # 1:4, mucho más alto
    assert y1 - y0 + 1 == DEST[1], "debería llenar el alto"
    assert x1 - x0 + 1 < DEST[0], "no debería llenar el ancho"
    assert abs(x0 - (DEST[0] - 1 - x1)) <= 1, "debería quedar centrado en horizontal"


@pytest.mark.parametrize("hacer", [
    lambda p: IMG.to_game_bmp(p, DEST, flat=True, encaja=True),
    lambda p: P7I.to_game_bmp(p, DEST, flatten=(0, 0, 0), flat=True, encaja=True),
], ids=["v56", "pcf7"])
def test_se_conserva_la_proporcion(hacer):
    """Un cuadrado tiene que seguir siendo un cuadrado."""
    x0, y0, x1, y1 = _caja(hacer(_png(300, 300)))
    ancho, alto = x1 - x0 + 1, y1 - y0 + 1
    assert abs(ancho - alto) <= 1, f"el cuadrado ha salido {ancho}x{alto}"


def test_estirando_un_cuadrado_se_deformaba():
    """Comprobación de que el modo de antes SÍ deformaba (por eso se cambió)."""
    x0, y0, x1, y1 = _caja(IMG.to_game_bmp(_png(300, 300), DEST, flat=True))
    assert (x1 - x0 + 1, y1 - y0 + 1) == DEST      # llena el lienzo entero: 48x64


@pytest.mark.parametrize("hacer", [
    lambda p: IMG.escudo_set(p),
    lambda p: P7I.escudo_set(p),
], ids=["v56", "pcf7"])
def test_escudo_set_usa_el_encuadre_nuevo(hacer):
    """El juego de escudos completo tiene que salir sin deformar."""
    juego = hacer(_png(300, 300))
    assert juego, "no ha generado ningún tamaño"
    for nombre, bmp in juego.items():
        x0, y0, x1, y1 = _caja(bmp)
        ancho, alto = x1 - x0 + 1, y1 - y0 + 1
        assert abs(ancho - alto) <= 2, f"{nombre}: cuadrado deformado a {ancho}x{alto}"
