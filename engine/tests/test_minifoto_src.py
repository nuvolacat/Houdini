"""La fuente de la minifoto se guarda REDUCIDA.

La minifoto del juego es de 32×32 y la fuente que queda en la sesión solo sirve para
generarla, así que arrastrar el original no aporta nada: un retrato a tamaño completo pesa
cientos de veces lo que se va a pintar.

Medido en un mod real de PCF7 el 2026-08-22: 12.102 minifotos ocupaban **1,79 GB**, y con
eso el proceso que lo tenía cargado se pasaba varios segundos en cada recogida de basura y
dejaba de responder. Reducidas, el mismo mod ocupa 0,14 GB.
"""
import io

from PIL import Image

from houdini_engine.codec import image as IMG


def _png(w, h, modo="RGBA"):
    im = Image.new(modo, (w, h), (200, 30, 40, 255) if modo == "RGBA" else (200, 30, 40))
    for x in range(0, w, 7):          # algo de detalle: si no, PNG comprime a nada
        for y in range(0, h, 5):
            im.putpixel((x, y), (10, 200, 90, 255) if modo == "RGBA" else (10, 200, 90))
    b = io.BytesIO(); im.save(b, format="PNG")
    return b.getvalue()


def test_un_retrato_grande_se_reduce_mucho():
    grande = _png(512, 512)
    chico = IMG.reduce_para_minifoto(grande)
    assert len(chico) < len(grande) / 4
    assert max(Image.open(io.BytesIO(chico)).size) <= IMG.MINI_SRC_MAX


def test_lo_que_ya_es_pequeno_no_se_toca():
    """Ni se recomprime ni se degrada: si ya cabe, se devuelve tal cual."""
    chico = _png(64, 64)
    assert IMG.reduce_para_minifoto(chico) is chico


def test_conserva_la_transparencia():
    """El retrato recortado viene recortado sobre transparente y el fondo se pone DESPUÉS:
    perder el alfa aquí dejaría la foto sobre un cuadro negro."""
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    im.paste((200, 40, 40, 255), (100, 100, 300, 300))
    b = io.BytesIO(); im.save(b, format="PNG")
    out = Image.open(io.BytesIO(IMG.reduce_para_minifoto(b.getvalue())))
    assert out.mode in ("RGBA", "LA", "P")
    assert out.convert("RGBA").getchannel("A").getextrema()[0] == 0   # sigue habiendo hueco


def test_la_minifoto_final_sigue_saliendo_de_32x32():
    """Lo que importa de verdad: reducir la fuente no cambia lo que acaba en el juego."""
    grande = _png(512, 512)
    directa = IMG.photo_set(grande, grande)["mini"]
    reducida = IMG.photo_set(grande, IMG.reduce_para_minifoto(grande))["mini"]
    assert Image.open(io.BytesIO(directa)).size == Image.open(io.BytesIO(reducida)).size


def test_una_imagen_ilegible_no_revienta_el_import():
    """Una foto corrupta no puede tumbar una actualización de 1.700 equipos."""
    assert IMG.reduce_para_minifoto(b"esto no es una imagen") == b"esto no es una imagen"
    assert IMG.reduce_para_minifoto(b"") == b""
