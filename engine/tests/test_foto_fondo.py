"""El fondo de las fotos de jugador.

Los retratos recortados vienen **recortados sobre transparente**. El fondo (metal cepillado azul,
generado por código en `photo_bg`) hay que ponérselo al GUARDAR la foto, no solo al escribir el
fichero del juego: si no, lo que queda en el mod —y lo que enseña la web— sigue teniendo alfa,
y se ve el fondo de la página a través del jugador o, al aplanarlo, un rectángulo negro.

Eso es justo lo que pasaba en 7/2000/2001, donde la foto se guardaba con `reduce_para_minifoto`,
que conserva la transparencia.
"""
from io import BytesIO

from PIL import Image

from houdini_engine.codec import image as IMG
from houdini_engine.codec import photo_bg


def _retrato_transparente(size=(512, 512)) -> bytes:
    """Un retrato sintético: 512×512 con la figura centrada y AIRE transparente alrededor.

    Lo del aire importa: es lo que deja ver el fondo por los lados de la cabeza. Antes aquí se
    pegaba un cuadrado que ocupaba media imagen a ras del borde, y con el encuadre nuevo —que
    llena el alto— tapaba el marco entero y parecía que el fondo había desaparecido. Medido en
    un retrato recortado típico."""
    from PIL import ImageDraw
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    piel = (200, 170, 150, 255)
    # cabeza: óvalo estrecho arriba, con aire a los lados (por ahí se ve el fondo)
    d.ellipse([w * 0.30, h * 0.05, w * 0.70, h * 0.62], fill=piel)
    # hombros: se ensanchan hacia abajo y llegan al borde inferior, como en los retratos recortados
    d.polygon([(w * 0.38, h * 0.55), (w * 0.62, h * 0.55), (w * 0.88, h), (w * 0.12, h)],
              fill=piel)
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _con_fondo(png: bytes) -> bytes:
    return IMG.con_fondo_si_transparente(png)


def test_detecta_la_transparencia():
    assert photo_bg.tiene_alfa(Image.open(BytesIO(_retrato_transparente())))


def test_al_guardar_deja_de_tener_alfa():
    """Lo importante: lo que se guarda ya es opaco, así que la web lo enseña bien."""
    out = Image.open(BytesIO(_con_fondo(_retrato_transparente())))
    assert not photo_bg.tiene_alfa(out), "la foto guardada sigue siendo transparente"


def _esquina(png: bytes):
    im = Image.open(BytesIO(png)).convert("RGB")
    esquina = [im.getpixel((x, y)) for x in range(4) for y in range(4)]
    return tuple(sum(c[i] for c in esquina) / len(esquina) for i in range(3))


def test_el_fondo_por_defecto_es_BLANCO():
    """Desde el 6-sep-2026 el fondo por defecto es el blanco de las fotos de prensa (el genérico,
    por defecto); nunca negro, que era el síntoma de aplanar la transparencia."""
    r, g, b = _esquina(_con_fondo(_retrato_transparente()))
    assert min(r, g, b) > 240, f"el fondo no es blanco: ({r:.0f},{g:.0f},{b:.0f})"


def test_el_fondo_metal_es_AZUL_no_negro():
    """Con «metal» elegido en Fotos: la rampa azul de la paleta del juego."""
    r, g, b = _esquina(IMG.con_fondo_si_transparente(_retrato_transparente(), fondo="metal"))
    assert b > r + 10, f"el fondo no es azulado: ({r:.0f},{g:.0f},{b:.0f})"
    assert b > 30, f"el fondo es casi negro: ({r:.0f},{g:.0f},{b:.0f})"


def test_una_foto_que_YA_trae_fondo_no_se_toca():
    """Las de prensa llegan con el suyo: se dejan igual, byte a byte."""
    buf = BytesIO()
    Image.new("RGB", (300, 390), (120, 140, 90)).save(buf, "PNG")
    original = buf.getvalue()
    assert _con_fondo(original) == original


def test_no_revienta_con_basura():
    assert _con_fondo(b"esto no es una imagen") == b"esto no es una imagen"
    assert _con_fondo(b"") == b""


def test_el_jugador_LLENA_el_alto():
    """El retrato recortado está cortado a la altura del cuello: cualquier hueco, arriba o abajo,
    hace que la foto parezca un recorte flotando. Se llena el alto y se recorta de los lados
    (2026-08-26: «salen sin cuello, empiezan en la barbilla»)."""
    im = Image.open(BytesIO(_con_fondo(_retrato_transparente()))).convert("RGB")
    w, h = im.size
    centro = range(w // 3, 2 * w // 3)
    fondo = im.getpixel((2, 2))
    for et, fila in (("abajo", h - 2), ("arriba", 1)):
        assert any(im.getpixel((x, fila)) != fondo for x in centro), \
            f"queda hueco de fondo {et}: la foto parece recortada"
