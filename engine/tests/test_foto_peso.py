"""Lo que se guarda de cada foto, y cuánto pesa.

Las fotos de jugador se guardaban tal como llegaban de la fuente —una foto grande o un retrato
recortado— y encima DOS veces: una para la ficha y otra para la
minifoto. El juego pinta 124×182 y 32×32, así que se guardaba dos veces y media la resolución
que se llega a ver, por duplicado.

No era un detalle: en un mod real de PC Fútbol 2001 eran **762 MB de fotos sobre 810 MB de
mod**.

Ahora se guarda UNA sola imagen por jugador, al tamaño de la ficha, y la minifoto sale de ella.
"""
from io import BytesIO

from PIL import Image

from houdini_engine.codec import image as IMG


def _foto(size=(300, 390), color=(150, 110, 90)) -> bytes:
    """Una foto de prensa como las que llegan: JPEG grande con algo de detalle."""
    im = Image.new("RGB", size, color)
    for i in range(0, size[1], 7):                    # textura, para que no comprima a nada
        for j in range(0, size[0], 5):
            im.putpixel((j, i), ((j * 7) % 255, (i * 3) % 255, (i + j) % 255))
    buf = BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def test_la_foto_guardada_es_del_tamaño_de_la_ficha():
    out = IMG.fuente_de_ficha(_foto())
    assert Image.open(BytesIO(out)).size == IMG.BIGFOTO_SIZE == (124, 182)


def test_pesa_bastante_menos_que_el_original():
    orig = _foto()
    out = IMG.fuente_de_ficha(orig)
    assert len(out) < len(orig) * 0.6, (
        f"solo baja de {len(orig)} a {len(out)} B; se esperaba al menos un 40% menos")


def test_una_foto_que_ya_esta_bien_no_se_reprocesa():
    """Reprocesar un JPEG lo degrada un poco cada vez; si ya está como la queremos, se deja
    tal cual (mismos bytes)."""
    buf = BytesIO()
    Image.new("RGB", IMG.BIGFOTO_SIZE, (80, 90, 100)).save(buf, "JPEG", quality=88)
    ya = buf.getvalue()
    assert IMG.fuente_de_ficha(ya) is ya or IMG.fuente_de_ficha(ya) == ya


def test_sigue_sirviendo_para_la_minifoto():
    """De la MISMA imagen tiene que salir la minifoto de 32×32 del juego, que es lo que
    permite guardar una sola."""
    from houdini_engine.codec import pcf7_image as P7I
    guardada = IMG.fuente_de_ficha(_foto())
    bmp = P7I.minifoto_bmp(guardada)      # el códec de PCF7, que es quien la escribe
    assert bmp[:2] == b"BM", "no ha salido un BMP del juego"
    assert len(bmp) > 100


def test_no_revienta_con_basura():
    assert IMG.fuente_de_ficha(b"") == b""
    assert IMG.fuente_de_ficha(b"esto no es una imagen") == b"esto no es una imagen"


def test_el_ahorro_es_el_esperado_de_punta_a_punta():
    """Antes: foto de ficha (300×390) + minifoto aparte. Ahora: una sola de 124×182.
    Se comprueba el conjunto, que es lo que llena el disco."""
    orig = _foto()
    antes = len(orig) + len(IMG.reduce_para_minifoto(orig))
    ahora = len(IMG.fuente_de_ficha(orig))
    assert ahora < antes * 0.5, f"antes {antes} B, ahora {ahora} B"


def test_una_foto_pequeña_se_reencuadra_aunque_pese_mas():
    """Guarda contra un fallo real: la función se quedaba con el original cuando el JPEG
    resultante pesaba más, y una foto de prensa de 100×130 pesa menos que su versión a
    124×182 → la ficha se guardaba con el tamaño equivocado. El peso no manda sobre el
    tamaño."""
    chica = _foto(size=(100, 130))
    out = IMG.fuente_de_ficha(chica)
    assert Image.open(BytesIO(out)).size == IMG.BIGFOTO_SIZE
