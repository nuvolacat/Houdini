"""Fondo de las fotos (17-sep-2026): el mismo encuadre con cualquier fondo, y fondo
PERSONALIZADO a partir de una imagen subida."""
from io import BytesIO

from PIL import Image, ImageDraw

from houdini_engine.codec import image as IMG

AZUL = (20, 60, 200)


def _prensa() -> bytes:
    """Foto de prensa: fondo blanco plano y un busto en medio."""
    im = Image.new("RGB", (300, 390), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((110, 80, 190, 180), fill=(200, 150, 120))      # cara
    d.rectangle((70, 190, 230, 390), fill=(180, 20, 30))      # camiseta
    b = BytesIO(); im.save(b, "PNG"); return b.getvalue()


def _png(color) -> bytes:
    b = BytesIO(); Image.new("RGB", (400, 300), color).save(b, "PNG"); return b.getvalue()


def _cerca(a, b, tol=6):  # la ficha va en JPEG: redondeo
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def _abre(b): return Image.open(BytesIO(IMG.fuente_de_ficha(b))).convert("RGB")


def test_mismo_encuadre_con_blanco_y_con_otro_fondo():
    src = _prensa()
    blanco = _abre(IMG.con_fondo_si_transparente(src, fondo="blanco"))
    metal = _abre(IMG.con_fondo_si_transparente(src, fondo="metal"))
    propio = _abre(IMG.con_fondo_si_transparente(src, fondo=_png(AZUL)))
    assert blanco.size == metal.size == propio.size == IMG.BIGFOTO_SIZE
    # la camiseta (el sujeto) cae en los MISMOS píxeles con los tres fondos
    def sujeto(im):
        return {(x, y) for x in range(0, im.width, 4) for y in range(0, im.height, 4)
                if im.getpixel((x, y))[0] > 150 and im.getpixel((x, y))[1] < 60}
    a, b, c = sujeto(blanco), sujeto(metal), sujeto(propio)
    assert a and len(a ^ b) <= len(a) * 0.05 and len(a ^ c) <= len(a) * 0.05


def test_fondo_personalizado_en_foto_de_prensa_y_en_retrato_recortado():
    propio = _png(AZUL)
    ficha = _abre(IMG.con_fondo_si_transparente(_prensa(), fondo=propio))
    assert _cerca(ficha.getpixel((2, 2)), AZUL)             # la esquina es el fondo subido
    retrato = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    ImageDraw.Draw(retrato).ellipse((150, 60, 360, 480), fill=(200, 150, 120, 255))
    b = BytesIO(); retrato.save(b, "PNG")
    ficha2 = _abre(IMG.con_fondo_si_transparente(b.getvalue(), fondo=propio))
    assert _cerca(ficha2.getpixel((2, 2)), AZUL)


def test_con_blanco_la_foto_de_prensa_no_se_toca():
    src = _prensa()
    assert IMG.con_fondo_si_transparente(src, fondo="blanco") == src


def test_el_blanco_de_la_camiseta_que_toca_el_borde_no_es_fondo():
    """Rayas blancas hasta el canto de abajo : no se pueden tratar como fondo."""
    im = Image.new("RGB", (300, 390), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((110, 80, 190, 180), fill=(200, 150, 120))
    d.rectangle((70, 190, 230, 390), fill=(20, 60, 180))
    for x in range(90, 230, 40):
        d.rectangle((x, 200, x + 15, 390), fill=(255, 255, 255))   # rayas blancas hasta abajo
    b = BytesIO(); im.save(b, "PNG")
    amarillo = _png((240, 200, 40))
    ficha = _abre(IMG.con_fondo_si_transparente(b.getvalue(), fondo=amarillo))
    abajo = [ficha.getpixel((x, ficha.height - 3)) for x in range(ficha.width // 4, ficha.width * 3 // 4)]
    assert not any(_cerca(px, (240, 200, 40), 30) for px in abajo)   # no se ve el fondo por las rayas


def test_la_fuente_de_la_minifoto_es_un_cuadrado_con_la_cara():
    """La minifoto salía de encajar la ficha vertical entera en el cuadrado (la cara quedaba diminuta)."""
    src = _prensa()
    ficha = IMG.fuente_de_ficha(src)
    mini = Image.open(BytesIO(IMG.fuente_de_minifoto(ficha))).convert("RGB")
    assert mini.size == (128, 128)
    # la cara (color piel) ocupa buena parte del ancho en el centro, no un hilo
    fila = [mini.getpixel((x, 50)) for x in range(128)]
    piel = sum(1 for r, g, b in fila if 170 < r < 230 and 120 < g < 180 and 90 < b < 150)
    assert piel > 40
