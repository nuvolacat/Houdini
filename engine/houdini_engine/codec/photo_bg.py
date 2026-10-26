"""Fondo para las fotos de jugador: metal cepillado azul.

Las fotos originales de PCF 5/6 son recortes de prensa, así que siempre tienen FONDO —
la portería detrás de Raúl, la grada de Kiko, el cielo de Batistuta— y encima se ve la
camiseta. Los retratos recortados, en cambio, vienen recortados sobre transparente: aplanados
sobre negro quedan nítidos pero cantan, porque en el juego ninguna foto tiene el fondo
negro.

La solución es ponerles un fondo de estudio, y el que mejor pega con la época es una
plancha de metal cepillado azul. Se GENERA por código en vez de traer una imagen:

  · no arrastra un fichero de stock al repo (ni su licencia),
  · es determinista —misma semilla, mismos píxeles— así que la descarga sigue siendo
    reproducible,
  · se dibuja directamente al tamaño pedido (124×182 y 32×32 son 22.000 y 1.000 píxeles),
    que es más rápido que generar uno grande y recortarlo.

Comprobado contra una textura de stock real: una vez reducido al marco y cuantizado a los
256 colores de la paleta de Dinamic, no se distinguen.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

# claro del foco y sombra del fondo. Azules apagados: tienen que quedar POR DETRÁS del
# jugador, no competir con la camiseta.
_CLARO = (228, 236, 250)
_OSCURO = (108, 132, 176)


@lru_cache(maxsize=8)
def brushed_metal(w: int, h: int, seed: int = 7) -> Image.Image:
    """Plancha de metal cepillado azul de `w`×`h`. Cacheada por tamaño."""
    im = Image.new("RGB", (w, h))
    px = im.load()
    # 1) foco de luz arriba a la izquierda con caída diagonal: es lo que lo hace parecer
    #    metal iluminado y no un degradado plano
    fx, fy = 0.30 * w, 0.10 * h
    dmax = math.hypot(w, h) or 1.0
    for y in range(h):
        for x in range(w):
            t = min(1.0, (math.hypot(x - fx, y - fy) / dmax * 1.35) ** 0.85)
            px[x, y] = tuple(round(_CLARO[i] + (_OSCURO[i] - _CLARO[i]) * t) for i in range(3))
    # 2) vetas horizontales = el "cepillado". Largo proporcional al ancho para que la
    #    textura se vea igual en la foto de ficha y en la minifoto.
    rnd = random.Random(seed)
    vetas = Image.new("L", (w, h), 128)
    d = ImageDraw.Draw(vetas)
    corto, largo = max(4, w // 20), max(10, w // 2)
    for _ in range(w * 3):
        y = rnd.randrange(h)
        x0 = rnd.randrange(-largo // 4, w)
        d.line([(x0, y), (x0 + rnd.randrange(corto, largo), y)],
               fill=128 + rnd.randrange(-26, 27))
    vetas = vetas.filter(ImageFilter.GaussianBlur(0.4))
    base, ruido = im.load(), vetas.load()
    for y in range(h):
        for x in range(w):
            k = (ruido[x, y] - 128) / 255 * 0.30
            r, g, b = base[x, y]
            base[x, y] = (min(255, round(r * (1 + k))),
                          min(255, round(g * (1 + k))),
                          min(255, round(b * (1 + k))))
    return im.filter(ImageFilter.GaussianBlur(0.3))


# Encuadre. La regla sale de mirar las fotos originales del juego: son bustos que LLENAN el
# marco, con la cabeza en la mitad de arriba y el torso hasta el borde de abajo. Nunca hay una
# banda de fondo vacía.
#
# El retrato recortado no da para tanto —viene cerrado sobre la cara, con un asomo de cuello— así
# que la regla practicable es:
#
#   · nada de huecos: se llena el ALTO, que es la dimensión que manda en un marco vertical;
#   · lo que sobra se recorta de los LADOS, por igual, que es donde el retrato tiene aire;
#   · la cabeza queda arriba y el cuello llega al borde inferior, como en las de Dinamic.
#
# Antes se encajaba entero (`min` de las dos escalas) y se pegaba abajo. Eso dejaba 49 px de
# fondo muerto arriba y la cabeza pequeña con el cuello justo en el canto: en el foro se leyó
# como "las fotos no tienen cuello, empiezan en la barbilla" (2026-08-26).


def con_fondo(retrato: Image.Image, size: tuple[int, int], fondo="blanco") -> Image.Image:
    """Compone un retrato RECORTADO (con alfa) sobre el metal, al estilo de las del juego.

    El retrato recortado es casi cuadrado  y el hueco de la
    ficha es alargado (124×182). Metiéndolo entero sobraban 49 px arriba: la cabeza quedaba
    pequeña, flotando, y el poco cuello que trae el retrato caía justo en el borde de abajo —
    parecía cortada por la barbilla, que es como se vio en el foro.

    Así que se llena el ALTO y se recorta de los lados, que es donde sobra: la cabeza ocupa el
    marco y abajo entran el cuello y el cuello de la camiseta. No llega a ser el busto con
    hombros de las fichas de Dinamic —ese cuerpo no está en esa imagen—, pero deja de
    leerse como un recorte."""
    fg = retrato.convert("RGBA")
    caja = fg.split()[-1].getbbox()          # fuera el aire transparente de alrededor
    if caja:
        fg = fg.crop(caja)
    k = size[1] / fg.height                              # llena el alto
    w = max(1, round(fg.width * k))
    fg = fg.resize((w, size[1]), Image.LANCZOS)
    lienzo = fondo_ficha(size, fondo)
    # centrado a lo ancho: recorta por igual a los dos lados si sobra, y deja aire simétrico
    # si el retrato viniera más estrecho que el hueco.
    lienzo.alpha_composite(fg, (-(w - size[0]) // 2, 0))
    return lienzo.convert("RGB")


FONDOS = ("blanco", "metal", "personalizado")


def fondo_ficha(size: tuple[int, int], fondo="blanco") -> Image.Image:
    """Lienzo RGBA del fondo elegido para el mod: «blanco» (el genérico de las fotos de prensa,
    sin coste), «metal» (la plancha azul cepillada) o una IMAGEN subida por el usuario (llega
    como bytes; 17-sep-2026). Se elige en Fotos y lo aplica el import y «Rehacer
    fotos» (2026-09-06)."""
    if isinstance(fondo, (bytes, bytearray)):
        from io import BytesIO
        from PIL import ImageOps
        img = Image.open(BytesIO(bytes(fondo)))
        img.load()
        return ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS).convert("RGBA")
    if fondo == "metal":
        return brushed_metal(size[0], size[1]).convert("RGBA")
    return Image.new("RGBA", size, (255, 255, 255, 255))


def tiene_alfa(img: Image.Image) -> bool:
    """¿La imagen viene recortada sobre transparente? Solo entonces hace falta el fondo:
    las fotos de prensa ya traen el suyo y no se tocan."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        a = img.convert("RGBA").split()[-1]
        lo, _hi = a.getextrema()
        return lo < 250            # hay píxeles no opacos
    return False
