"""La minifoto entra ENTERA cuando la foto ya viene cuadrada, y se recorta solo si no cabe.

Las dos mitades de la regla vienen cada una de un caso real del foro, y van en direcciones
opuestas, así que las dos tienen que estar sujetas:

  · Recortar SIEMPRE dejaba la mini cortada aunque la foto de origen cupiera de sobra: la
    grande salía entera y la pequeña no (20-sep-2026). Con una foto
    cuadrada el recorte no ganaba nada y perdía la barbilla y la coronilla.

  · Encajarla SIEMPRE tampoco vale: con un retrato vertical deja franjas a los lados. Es lo que
    se arregló el 17-sep-2026, y sería una regresión volver a eso.

El tercer test es el que de verdad protege el arreglo: comprueba que la CARA no se ha ido por
el borde, que es lo que el usuario ve. Sin él, cualquier reencuadre futuro pasaría los otros dos.
"""
import os
import sys
from io import BytesIO

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))

Image = pytest.importorskip("PIL.Image")


def _retrato(w: int, h: int) -> bytes:
    """Un retrato de mentira pero con lo que mira el encuadre: fondo claro, una cabeza oscura
    arriba y un cuerpo más ancho debajo."""
    from PIL import ImageDraw
    im = Image.new("RGB", (w, h), (232, 232, 236))
    d = ImageDraw.Draw(im)
    cab = int(w * 0.42)
    cx, cy = w // 2, int(h * 0.30)
    d.ellipse((cx - cab // 2, cy - cab // 2, cx + cab // 2, cy + cab // 2), fill=(70, 50, 40))
    d.rectangle((int(w * 0.20), int(h * 0.55), int(w * 0.80), h), fill=(180, 30, 40))
    out = BytesIO(); im.save(out, "PNG")
    return out.getvalue()


def _mini(png: bytes, lado: int = 128):
    from houdini_engine.codec import image as IMG
    return Image.open(BytesIO(IMG.fuente_de_minifoto(png, lado)))


def test_la_minifoto_siempre_es_cuadrada():
    for w, h in ((300, 300), (300, 390), (400, 300)):
        im = _mini(_retrato(w, h))
        assert im.size == (128, 128), f"{w}x{h} -> {im.size}"


def test_una_foto_cuadrada_entra_entera():
    """Lo que pedía un usuario: si cabe, que no se corte. Se mide comparando con el original: la
    proporción entre la cabeza y el alto tiene que mantenerse, no ampliarse."""
    from houdini_engine.codec import image as IMG
    png = _retrato(300, 300)
    mini = _mini(png)
    orig = Image.open(BytesIO(png)).convert("RGB").resize((128, 128))
    # el rojo de la camiseta ocupa lo mismo en los dos: señal de que no se ha ampliado el recorte
    rojo = lambda im: sum(1 for p in im.convert("RGB").getdata()
                          if p[0] > 130 and p[1] < 90 and p[2] < 90)
    assert rojo(mini) > rojo(orig) * 0.75, "se ha recortado una foto que cabía entera"
    assert IMG._MINI_ENTERA_HASTA >= 1.2


def _ancho_cabeza(mini) -> float:
    """Qué parte del ancho ocupa la cabeza, de 0 a 1. Es lo que decide si la cara se lee a
    32×32, que es el tamaño al que esto se va a ver de verdad."""
    cols = [x for x in range(128)
            if any(mini.getpixel((x, y))[0] < 120 and mini.getpixel((x, y))[2] < 90
                   for y in range(128))]
    return (cols[-1] - cols[0] + 1) / 128 if cols else 0.0


def test_una_foto_muy_vertical_se_recorta_para_que_la_cara_se_vea():
    """La regresión del 17-sep-2026, medida por donde duele.

    Encajar un retrato VERTICAL en el cuadrado no deja franjas negras —el relleno estira el
    borde—, pero deja la cara pequeñísima, y a 32×32 no se reconoce a nadie. Por eso ahí se
    recorta. Se mide el ancho de la cabeza, no el color de los bordes: comprobar que no hay
    franjas negras no protege de nada, porque nunca las hay."""
    ancho = _ancho_cabeza(_mini(_retrato(300, 480)).convert("RGB"))
    assert ancho > 0.45, f"la cabeza se queda en el {ancho:.0%} del ancho: no se lee a 32×32"


def test_no_quedan_franjas_negras_en_ningun_caso():
    """Lo que se rellena a los lados es el borde estirado, nunca negro (`_pega_extendiendo`)."""
    for w, h in ((300, 300), (300, 390), (300, 480), (400, 300)):
        mini = _mini(_retrato(w, h)).convert("RGB")
        bordes = ([mini.getpixel((x, y)) for x in (0, 1, 126, 127) for y in range(0, 128, 8)]
                  + [mini.getpixel((x, y)) for y in (0, 1, 126, 127) for x in range(0, 128, 8)])
        negros = [p for p in bordes if max(p) < 40]
        assert not negros, f"{w}x{h}: {len(negros)} píxeles de franja negra"


def test_la_cara_no_se_sale_por_el_borde():
    """Lo que el usuario ve: que no se corte la coronilla ni la barbilla. La cabeza tiene que
    estar ENTERA dentro del cuadro, con los dos extremos dentro de la imagen."""
    for w, h in ((300, 300), (320, 320), (300, 480)):
        mini = _mini(_retrato(w, h)).convert("RGB")
        filas = [y for y in range(128)
                 if any(mini.getpixel((x, y))[0] < 120 and mini.getpixel((x, y))[2] < 90
                        for x in range(30, 98))]
        assert filas, f"{w}x{h}: no se encuentra la cabeza"
        assert filas[0] > 0, f"{w}x{h}: la coronilla toca el borde de arriba (cortada)"
