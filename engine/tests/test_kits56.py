"""Dibujo de la equipación del simulador de PC Fútbol 5 y 6.

Aquí la equipación no es una imagen como en 7/2000/2001: son 192 índices de la paleta VGA en
`DATSIM.PKF`, y para verla en la ficha hay que pintarla. Lo que se comprueba es que los colores
que salen son los del equipo de verdad —el Barça azulgrana, el Madrid blanco—, porque es lo
único que hace útil el dibujo; si los colores no son los suyos, mejor no enseñar nada.

Se salta si no está la gamedata (no va al repo: grande y con copyright).
"""
from io import BytesIO
from pathlib import Path

import pytest

from houdini_engine.formats import kits56 as K
from houdini_engine.formats import pantallas_pkf as PANT

GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
DATSIM = GAMEDATA / "pcf6oro" / "DATSIM.PKF"
BARCELONA, MADRID, ZARAGOZA = 1, 4, 2


@pytest.fixture(scope="module")
def datsim():
    if not DATSIM.exists():
        pytest.skip("sin gamedata de 6.0 Oro")
    data = DATSIM.read_bytes()
    byname = {e.name.upper(): e for e in PANT.entries(data)}
    e = byname["NUMCAM.BMP"]
    return data, byname, K.palette_from_bmp(data[e.off:e.off + e.size])


def _kit(datsim, ptr: int, lado: str = "A") -> bytes:
    data, byname, _pal = datsim
    e = byname[f"P96{lado}{ptr:04d}.DAT"]
    return data[e.off:e.off + e.size]


def test_la_paleta_del_simulador_sale_del_propio_juego(datsim):
    """Blanco, azul y rojo en los índices que usan las equipaciones."""
    pal = datsim[2]
    assert len(pal) == 256
    assert pal[0x7F] == (255, 255, 255), "0x7F debería ser el blanco"
    r, g, b = pal[0x80]
    assert r > 200 and g < 60 and b < 60, f"0x80 debería ser rojo, es {pal[0x80]}"
    r, g, b = pal[0x8C]
    assert b > 200 and r < 60, f"0x8C debería ser azul, es {pal[0x8C]}"


def test_un_kit_son_192_bytes(datsim):
    assert len(_kit(datsim, BARCELONA)) == K.KIT_LEN


def test_dibuja_un_png(datsim):
    from PIL import Image
    png = K.render_png(_kit(datsim, BARCELONA), datsim[2])
    im = Image.open(BytesIO(png))
    assert im.format == "PNG" and im.size == K.TAM


def test_la_rejilla_de_la_camiseta_es_16x8(datsim):
    """No una tira por columnas, que es lo que se creyó al principio: son 128 bytes = 16×8, y
    por eso el Barça tiene sus ocho filas idénticas (rayas verticales)."""
    assert K.COLS * K.FILAS == 128
    rej = _kit(datsim, BARCELONA)[:128]
    filas = {bytes(rej[f * 16:(f + 1) * 16]) for f in range(8)}
    assert len(filas) == 1, "las ocho filas del Barça deberían ser iguales"
    assert bytes(rej[:4]) == bytes.fromhex("8c80808c")


def test_ida_y_vuelta_sin_tocar_nada_no_cambia_un_byte(datsim):
    """Descargar la equipación y volver a subirla tal cual tiene que dejar el fichero igual.
    Se comprueba en TODAS las del juego, que es donde salieron los fallos: la rejilla no era
    una tira periódica, y las medias no son "color + vuelta" sino tres tonos por pierna."""
    data, byname, pal = datsim
    n = 0
    for nombre, e in byname.items():
        if not (nombre.startswith(("P96A", "P96B")) and nombre.endswith(".DAT")):
            continue
        kit = data[e.off:e.off + e.size]
        if len(kit) < K.KIT_LEN:
            continue                      # P96A0000 es la paleta base, de 256 B
        assert K.png_to_kit(K.render_png(kit, pal), kit, pal) == kit[:K.KIT_LEN], nombre
        n += 1
    assert n > 1000, f"solo se han probado {n} equipaciones"


def test_al_editar_el_dibujo_cambian_los_bytes(datsim):
    """Y lo que el dibujo NO enseña se conserva de la de partida, no se inventa."""
    from PIL import Image
    pal = datsim[2]
    kit = _kit(datsim, MADRID)
    im = Image.open(BytesIO(K.render_png(kit, pal))).convert("RGB")
    im.paste(pal[0x80], (K.MARGEN, K.MARGEN, K.MARGEN + 8, K.MARGEN + 8))   # 1ª celda a rojo
    buf = BytesIO(); im.save(buf, "PNG")
    nuevo = K.png_to_kit(buf.getvalue(), kit, pal)
    assert nuevo[0] == 0x80, "la celda pintada no se ha guardado"
    assert nuevo[1:128] == kit[1:128], "ha tocado celdas que no debía"
    assert nuevo[128:153] == kit[128:153], "la rampa y las constantes deben conservarse"
    assert nuevo[162:192] == kit[162:192], "la tercera zona debe conservarse"


def _colores(png: bytes) -> set:
    from PIL import Image
    im = Image.open(BytesIO(png)).convert("RGB")
    return {c for _n, c in im.getcolors(60000)}


def _hay(colores, pred) -> bool:
    return any(pred(*c) for c in colores)


def test_el_barcelona_sale_azulgrana(datsim):
    """El caso que más se nota: su rejilla es `8c 80 80 8c`, o sea azul y rojo alternos."""
    c = _colores(K.render_png(_kit(datsim, BARCELONA), datsim[2]))
    assert _hay(c, lambda r, g, b: b > 180 and r < 70), "no hay azul"
    assert _hay(c, lambda r, g, b: r > 180 and b < 70), "no hay rojo/grana"


def test_el_madrid_sale_blanco_y_sin_azul_ni_rojo(datsim):
    c = _colores(K.render_png(_kit(datsim, MADRID), datsim[2]))
    assert _hay(c, lambda r, g, b: r > 200 and g > 200 and b > 200), "no hay blanco"
    assert not _hay(c, lambda r, g, b: b > 180 and r < 70), "no debería tener azul"


def test_el_barcelona_sale_a_rayas_no_a_dos_mitades(datsim):
    """Con el dibujo viejo (estirando la rejilla al ancho del torso) el patrón caía siempre en
    el mismo color y la camiseta salía a dos mitades. Se cuentan los cambios de color a lo
    ancho del pecho."""
    from PIL import Image
    im = Image.open(BytesIO(K.render_png(_kit(datsim, BARCELONA), datsim[2]))).convert("RGB")
    y = K.MARGEN + 4 * K.CELDA
    fila = [im.getpixel((x, y)) for x in range(K.MARGEN, K.MARGEN + K.COLS * K.CELDA)]
    cambios = sum(1 for i in range(1, len(fila)) if fila[i] != fila[i - 1])
    assert cambios >= 6, f"solo {cambios} cambios de color: parece a mitades, no a rayas"


def test_la_segunda_equipacion_tambien_esta(datsim):
    assert len(_kit(datsim, BARCELONA, "B")) == K.KIT_LEN
    assert K.render_png(_kit(datsim, BARCELONA, "B"), datsim[2])


def test_un_kit_corto_se_rechaza(datsim):
    with pytest.raises(ValueError):
        K.render_png(b"\x7f" * 100, datsim[2])
