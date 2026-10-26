"""Cómo se encuadra el retrato recortado en la ficha del juego.

Reportado en el foro (2026-08-26): *"las fotos de las fichas salen los jugadores sin cuello,
todas empiezan en la barbilla"*. Los retratos recortados sí traen cuello; el corte lo hacíamos nosotros.

El retrato recortado es casi cuadrado y el hueco de la ficha es alargado (124×182).
Se metía entero y se pegaba abajo, así que quedaban 49 px de fondo muerto arriba y el poco
cuello del retrato caía justo en el canto inferior. Ahora se llena el alto y se recorta de los
lados, que es donde el retrato tiene aire.
"""
from PIL import Image

from houdini_engine.codec import photo_bg

FICHA = (124, 182)


def _retrato(size=(456, 489)) -> Image.Image:
    """Un retrato como los retratos recortados: contenido opaco sobre transparente, casi cuadrado."""
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    cara = Image.new("RGBA", size, (200, 170, 150, 255))
    im.paste(cara, ((512 - size[0]) // 2, 512 - size[1]), cara)
    return im


def _sin_fondo(im: Image.Image) -> tuple[int, int]:
    """(primera, última) fila que NO es fondo, para saber dónde queda el jugador."""
    px = im.convert("RGB").load()
    filas = [y for y in range(im.height)
             if any(px[x, y][0] > 180 and px[x, y][2] < 200 for x in range(im.width))]
    return (min(filas), max(filas)) if filas else (-1, -1)


def test_el_jugador_llena_el_alto_de_la_ficha():
    """Ni banda arriba ni hueco abajo: es lo que hacía que pareciera recortado."""
    out = photo_bg.con_fondo(_retrato(), FICHA)
    assert out.size == FICHA
    arriba, abajo = _sin_fondo(out)
    assert arriba == 0, f"queda una banda de fondo de {arriba} px arriba"
    assert abajo == FICHA[1] - 1, "queda hueco por debajo del jugador"


def test_el_recorte_se_reparte_entre_los_dos_lados():
    """Si se recortara solo de un lado, las caras saldrían descentradas."""
    out = photo_bg.con_fondo(_retrato(), FICHA)
    px = out.convert("RGB").load()
    fila = FICHA[1] // 2
    izq = [x for x in range(FICHA[0]) if px[x, fila][0] > 180 and px[x, fila][2] < 200]
    assert izq, "no se ve al jugador en mitad de la foto"
    margen_izq, margen_der = izq[0], FICHA[0] - 1 - izq[-1]
    assert abs(margen_izq - margen_der) <= 1, f"descentrado: {margen_izq} vs {margen_der}"


def test_un_retrato_estrecho_no_se_estira():
    """Si viniera más estrecho que el hueco se deja aire a los lados, no se deforma."""
    out = photo_bg.con_fondo(_retrato(size=(120, 480)), FICHA)
    assert out.size == FICHA
    px = out.convert("RGB").load()
    assert not (px[0, FICHA[1] // 2][0] > 180 and px[0, FICHA[1] // 2][2] < 200), \
        "el retrato llega al borde: se ha estirado"


def test_la_proporcion_de_la_cara_se_conserva():
    """Estirar para llenar deformaría las caras; hay que escalar igual en los dos ejes."""
    alto_util = 489
    ancho_util = 456
    out = photo_bg.con_fondo(_retrato(), FICHA)
    px = out.convert("RGB").load()
    fila = FICHA[1] // 2
    visible = [x for x in range(FICHA[0]) if px[x, fila][0] > 180 and px[x, fila][2] < 200]
    k = FICHA[1] / alto_util                       # la escala que se aplica al alto
    esperado = min(FICHA[0], round(ancho_util * k))
    assert abs(len(visible) - esperado) <= 2, f"ancho {len(visible)}, esperado {esperado}"


def test_una_foto_de_prensa_no_pasa_por_aqui():
    """Las de prensa ya traen su fondo y su encuadre: solo se compone lo transparente."""
    opaca = Image.new("RGB", (300, 390), (120, 130, 140))
    assert not photo_bg.tiene_alfa(opaca)
