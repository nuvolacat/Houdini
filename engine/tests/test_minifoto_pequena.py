"""Una foto pequeña hecha a mano tiene que llenar el marco, no quedarse en un rincón.

Petición del foro (22-sep-2026): tiene minifotos de 32×32 «hechas a la antigua
usanza» y al meterlas en el editor salían **a marco parcial**.

La causa: la fuente de la minifoto se escalaba con `Image.thumbnail`, que **solo reduce, nunca
amplía**. Una foto de 32×32 se quedaba a su tamaño en medio del lienzo de 128 y lo que rodeaba
era borde estirado. Medido con una «cara» que en el original ocupaba el 50% del ancho: salía
al **12%**, o sea a la cuarta parte de su tamaño.

Al ampliar se usa NEAREST si el factor es entero —32→128 es ×4 justo, que es el caso de estas
fotos antiguas— para que los píxeles se dupliquen tal cual en vez de emborronarse. Para
cualquier otro factor, LANCZOS de siempre.
"""
import io
import os
import sys

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "engine"))


def _cara(w, h, fx=(0.25, 0.75), fy=(0.2, 0.8)):
    """Una imagen de prueba con una «cara» azul sobre fondo verde, en una proporción conocida."""
    from PIL import Image
    im = Image.new("RGB", (w, h), (0, 160, 0))
    for x in range(int(w * fx[0]), int(w * fx[1])):
        for y in range(int(h * fy[0]), int(h * fy[1])):
            im.putpixel((x, y), (0, 0, 255))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _ocupa(png):
    """Qué porcentaje del ancho ocupa la «cara» en el resultado."""
    from PIL import Image
    r = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = r.size
    px = r.load()
    xs = [x for x in range(w) for y in range(h) if px[x, y][2] > 180 and px[x, y][1] < 100]
    return (0 if not xs else 100 * (max(xs) - min(xs) + 1) / w), r.size


@pytest.mark.parametrize("w,h", [(32, 32), (48, 48), (64, 64), (100, 100)])
def test_una_foto_pequena_llena_el_marco(w, h):
    """Lo que pedía un usuario: la cara tiene que ocupar en la fuente lo mismo que en su foto."""
    from houdini_engine.codec import image as IMG
    pct, tam = _ocupa(IMG.fuente_de_minifoto(_cara(w, h)))
    assert tam == (128, 128)
    assert 45 <= pct <= 55, f"{w}×{h}: la cara ocupa el {pct:.0f}% y en el original el 50%"


def test_antes_se_quedaba_a_un_cuarto():
    """El tamaño del fallo, para que se vea qué se arregló: con `thumbnail` la foto de 32×32
    no se ampliaba y la cara salía al 12% en vez de al 50%."""
    from PIL import Image
    from houdini_engine.codec import image as IMG
    im = Image.open(io.BytesIO(_cara(32, 32))).convert("RGB")
    viejo = im.copy()
    viejo.thumbnail((128, 128), Image.LANCZOS)
    assert viejo.size == (32, 32), "`thumbnail` ya no se comporta así: revisar este test"
    nuevo = IMG._escala_para_caber(im, 128)
    assert nuevo.size == (128, 128)


def test_las_fotos_grandes_se_siguen_reduciendo_igual():
    """Lo que ya funcionaba no cambia: una foto normal se reduce al lienzo como siempre."""
    from houdini_engine.codec import image as IMG
    for lado in (200, 400, 1024):
        pct, tam = _ocupa(IMG.fuente_de_minifoto(_cara(lado, lado)))
        assert tam == (128, 128)
        assert 45 <= pct <= 55, f"{lado}: {pct:.0f}%"


def test_al_ampliar_por_un_entero_no_se_emborrona():
    """32→128 es ×4 exacto: los píxeles se duplican tal cual, que es lo que quiere quien
    dibuja una foto a mano. Se comprueba contando colores: un escalado suave inventa tonos
    intermedios entre el verde y el azul, y NEAREST no."""
    from PIL import Image
    from houdini_engine.codec import image as IMG
    im = Image.open(io.BytesIO(_cara(32, 32))).convert("RGB")
    ampliada = IMG._escala_para_caber(im, 128)
    colores = {c for _n, c in ampliada.getcolors(maxcolors=100000)}
    assert colores == {(0, 160, 0), (0, 0, 255)}, f"ha inventado tonos: {len(colores)} colores"


def test_al_ampliar_por_un_factor_raro_se_suaviza():
    """100→128 no es entero: ahí sí conviene LANCZOS, porque duplicar píxeles a trozos
    dejaría escalones."""
    from PIL import Image
    from houdini_engine.codec import image as IMG
    im = Image.open(io.BytesIO(_cara(100, 100))).convert("RGB")
    ampliada = IMG._escala_para_caber(im, 128)
    assert ampliada.size == (128, 128)
    assert len(ampliada.getcolors(maxcolors=100000)) > 2, "no ha suavizado nada"


def test_una_foto_que_ya_mide_el_lado_no_se_toca():
    from PIL import Image
    from houdini_engine.codec import image as IMG
    im = Image.open(io.BytesIO(_cara(128, 128))).convert("RGB")
    assert IMG._escala_para_caber(im, 128) is im


def test_una_foto_vertical_pequena_tambien_llena():
    """Por encima de la proporción límite se recorta a primer plano en vez de encajar, pero
    tampoco puede quedarse pequeña en medio del lienzo."""
    from houdini_engine.codec import image as IMG
    pct, tam = _ocupa(IMG.fuente_de_minifoto(_cara(32, 64)))
    assert tam == (128, 128)
    assert pct > 30, f"la cara ocupa solo el {pct:.0f}%"


def test_no_se_rompe_con_una_imagen_de_un_pixel():
    from houdini_engine.codec import image as IMG
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1, 1), (10, 20, 30)).save(b, "PNG")
    r = Image.open(io.BytesIO(IMG.fuente_de_minifoto(b.getvalue())))
    assert r.size == (128, 128)
