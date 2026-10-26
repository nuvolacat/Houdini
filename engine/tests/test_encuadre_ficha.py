"""El encuadre de la foto: la cabeza en la proporción de Dinamic, no llenando el marco.

Las fichas del juego son un plano de busto —la cabeza ocupa ~36% del ancho y la coronilla queda
al 5% del alto, medido sobre `DBDAT/BIGFOTO` de PCF7—; el editor hacía un "cover" anclado arriba
y el rostro se comía el hueco (foro, 13-sep-2026).
"""
from PIL import Image, ImageDraw
import pytest

from houdini_engine.codec.image import _cabeza, encuadre_ficha

FICHA = (124, 182)


def retrato(w=300, h=300, cabeza=110, arriba=20, fondo=(255, 255, 255)) -> Image.Image:
    """Retrato sintético con fondo plano: cabeza (elipse), cuello y hombros."""
    im = Image.new("RGB", (w, h), fondo)
    d = ImageDraw.Draw(im)
    cx = w // 2
    alto_cab = round(cabeza * 1.3)
    d.ellipse([cx - cabeza // 2, arriba, cx + cabeza // 2, arriba + alto_cab], fill=(210, 170, 140))
    cuello = arriba + alto_cab
    d.rectangle([cx - cabeza // 5, cuello - 6, cx + cabeza // 5, cuello + 14], fill=(200, 160, 130))
    d.ellipse([cx - cabeza, cuello + 10, cx + cabeza, h + cabeza], fill=(30, 40, 90))
    return im


def test_mide_la_cabeza():
    x0, x1, y0 = _cabeza(retrato(cabeza=110, arriba=20))
    assert abs((x1 - x0) - 110) <= 6           # el ancho de la cabeza, no el de los hombros
    assert abs(y0 - 20) <= 3                   # la coronilla
    assert abs((x0 + x1) / 2 - 150) <= 4       # centrada


def test_no_confunde_los_hombros_con_la_cabeza():
    # hombros MUY anchos: la medida no puede irse con ellos
    x0, x1, _y = _cabeza(retrato(w=400, cabeza=90, arriba=15))
    assert (x1 - x0) < 130


def test_la_cabeza_queda_en_la_proporcion_del_juego():
    im = retrato(cabeza=110, arriba=20)
    out = encuadre_ficha(im, FICHA)
    assert out.size == FICHA
    x0, x1, y0 = _cabeza(out)
    # elegido (17-sep-2026): cabeza al 66% del ancho (Dinamic usaba el 36%)
    assert 0.58 <= (x1 - x0) / FICHA[0] <= 0.74
    assert y0 <= FICHA[1] * 0.14                   # la coronilla, arriba y con aire


def test_la_minifoto_es_un_primer_plano():
    # la minifoto de 32×32 del juego SÍ es un primer plano: la cabeza llena el cuadro
    out = encuadre_ficha(retrato(cabeza=110, arriba=20), (32, 32))
    assert out.size == (32, 32)
    x0, x1, _y = _cabeza(out.resize((256, 256), Image.NEAREST))   # `_cabeza` pide 40 px o más
    assert (x1 - x0) / 256 >= 0.55


def test_es_estable_al_repetirlo():
    # la ficha guardada se vuelve a encuadrar al armar la descarga: no puede irse zoom a zoom
    una = encuadre_ficha(retrato(), FICHA)
    dos = encuadre_ficha(una, FICHA)
    a, b = _cabeza(una), _cabeza(dos)
    assert abs((a[1] - a[0]) - (b[1] - b[0])) <= 4
    assert abs(a[2] - b[2]) <= 4


def test_sin_fondo_plano_no_se_mide_y_no_revienta():
    ruido = Image.effect_noise((300, 300), 60).convert("RGB")
    assert _cabeza(ruido) is None
    assert encuadre_ficha(ruido, FICHA).size == FICHA


def test_una_foto_diminuta_no_rompe():
    assert _cabeza(Image.new("RGB", (12, 12), "white")) is None
    assert encuadre_ficha(Image.new("RGB", (12, 12), "white"), FICHA).size == FICHA


@pytest.mark.parametrize("size", [(124, 182), (32, 32), (24, 24), (73, 38)])
def test_siempre_devuelve_el_tamano_pedido(size):
    assert encuadre_ficha(retrato(), size).size == size
