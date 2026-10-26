"""El negro de un escudo no puede acabar en el índice 0: el juego lo pinta transparente.

Dinamic reservó el índice 0 para el fondo y pintó el negro del dibujo con el 135, (22,22,22).
Verificado sobre los escudos originales de 5.0 Oro: las cuatro esquinas de todos son índice 0
y el negro del dibujo es el 135 (en el del Barakaldo, 9.676 píxeles de sus rayas).

Sin esto, un escudo con negro —rayas de Barakaldo o Juventus, un contorno oscuro— sale
agujereado dentro del juego: por sus zonas negras se ve el fondo de la pantalla.
"""
from io import BytesIO

import pytest

from houdini_engine.codec import image as IMG

Image = pytest.importorskip("PIL.Image")


def _png(size=(64, 64), *, con_alfa=True):
    """Cuadro NEGRO OPACO centrado sobre fondo transparente (o blanco si no hay alfa)."""
    fondo = (0, 0, 0, 0) if con_alfa else (255, 255, 255, 255)
    im = Image.new("RGBA", size, fondo)
    for x in range(size[0] // 4, size[0] * 3 // 4):
        for y in range(size[1] // 4, size[1] * 3 // 4):
            im.putpixel((x, y), (0, 0, 0, 255))       # negro OPACO = parte del dibujo
    if not con_alfa:
        im = im.convert("RGB")
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _indices(bmp: bytes):
    im = Image.open(BytesIO(bmp))
    assert im.mode == "P"
    return im, list(im.getdata())


def test_el_negro_del_dibujo_no_cae_en_el_indice_0():
    bmp = IMG.to_game_bmp(_png(), (48, 64), flat=True)
    im, px = _indices(bmp)
    w, h = im.size
    centro = im.load()[w // 2, h // 2]
    assert centro != 0, "el negro del dibujo se ha ido al índice 0 (el juego lo hará transparente)"


def test_el_negro_del_dibujo_usa_el_casi_negro_de_dinamic():
    bmp = IMG.to_game_bmp(_png(), (48, 64), flat=True)
    im, _ = _indices(bmp)
    pal = IMG._palette()
    idx = im.load()[im.size[0] // 2, im.size[1] // 2]
    assert tuple(pal[idx * 3:idx * 3 + 3]) == IMG._NEGRO_VISIBLE


def test_el_fondo_transparente_sigue_siendo_el_indice_0():
    """Lo que era transparente NO se toca: si se subiera también, el escudo saldría con
    un recuadro de fondo en vez de recortado."""
    bmp = IMG.to_game_bmp(_png(), (48, 64), flat=True)
    im, _ = _indices(bmp)
    w, h = im.size
    px = im.load()
    for esquina in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        assert px[esquina] == 0, f"la esquina {esquina} debería ser fondo transparente"


def test_sin_canal_alfa_no_se_toca_nada():
    """Sin alfa, un fondo negro recortado ES la transparencia; subirlo pintaría un recuadro."""
    antes = IMG.to_game_bmp(_png(con_alfa=False), (48, 64), flat=True)
    im, _ = _indices(antes)
    px = im.load()
    assert px[im.size[0] // 2, im.size[1] // 2] == 0


def test_las_fotos_no_se_ven_afectadas():
    """`flat` es de escudos y banderas; una foto (sin flat) sigue su camino de siempre."""
    bmp = IMG.to_game_bmp(_png(), (32, 32), flat=False)
    im, _ = _indices(bmp)
    assert im.size == (32, 32)


# ------------------------------------------------------------------- PCF7/2000/2001
# Misma convención, verificada sobre 60 escudos originales de PCF7: sus 240 esquinas son
# índice 0 y el negro del dibujo es el MISMO índice 135, (22,22,22).
from houdini_engine.codec import pcf7_image as P7I  # noqa: E402


def test_pcf7_el_negro_del_dibujo_no_cae_en_el_indice_0():
    bmp = P7I.to_game_bmp(_png(), (48, 64), flatten=(0, 0, 0), flat=True)
    im = Image.open(BytesIO(bmp))
    assert im.load()[im.size[0] // 2, im.size[1] // 2] != 0


def test_pcf7_el_fondo_transparente_sigue_siendo_el_indice_0():
    bmp = P7I.to_game_bmp(_png(), (48, 64), flatten=(0, 0, 0), flat=True)
    im = Image.open(BytesIO(bmp))
    w, h = im.size
    px = im.load()
    for esquina in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        assert px[esquina] == 0


def test_pcf7_con_fondo_blanco_no_se_toca():
    """Cuando el transparente es BLANCO (otras imágenes de PCF7), esto no debe actuar."""
    bmp = P7I.to_game_bmp(_png(), (48, 64), flatten=(255, 255, 255), flat=True)
    im = Image.open(BytesIO(bmp))
    pal = P7I._palette("main")
    idx = im.load()[im.size[0] // 2, im.size[1] // 2]
    assert tuple(pal[idx * 3:idx * 3 + 3]) != IMG._NEGRO_VISIBLE


def _png_colores(size=(64, 64)):
    """Escudo con colores SATURADOS opacos (rojo, azul, amarillo) sobre transparente.
    Todos tienen algún canal a 0, que es justo lo que confundía a la máscara."""
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    tercio = size[1] // 3
    for i, col in enumerate(((210, 0, 0), (0, 0, 190), (255, 223, 0))):
        for x in range(size[0] // 4, size[0] * 3 // 4):
            for y in range(i * tercio, (i + 1) * tercio):
                im.putpixel((x, y), col + (255,))
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.parametrize("banda,esperado", [(0, "rojo"), (1, "azul"), (2, "amarillo")])
def test_los_colores_saturados_no_se_toman_por_negro(banda, esperado):
    """REGRESIÓN: un rojo puro es (210,0,0) — dos canales a 0. Si la máscara mira el
    MÍNIMO de los canales en vez del máximo, se lo come y pinta el escudo de gris."""
    bmp = IMG.to_game_bmp(_png_colores(), (48, 64), flat=True)
    im = Image.open(BytesIO(bmp))
    pal = IMG._palette()
    w, h = im.size
    idx = im.load()[w // 2, h // 6 + banda * (h // 3)]
    rgb = tuple(pal[idx * 3:idx * 3 + 3])
    assert rgb != IMG._NEGRO_VISIBLE, f"el {esperado} se ha convertido en casi-negro"
    assert max(rgb) > 100, f"el {esperado} ha salido oscuro: {rgb}"
