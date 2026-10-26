"""Códec de imágenes de PCF (escudos y fotos).

El juego usa BMP de 256 colores con una **paleta fija** (la VGA estándar de Windows,
extraída de las plantillas oficiales). El editor de referencia no repacka los
contenedores PKF: coloca **BMP sueltos** en DBDAT\\NANOESC\\, \\MINIESC\\,
\\RIDIESC\\ (escudos, `eq{96|97}{ptr_equipo:04d}.bmp`) y \\MINIFOTO\\ (fotos,
`j{96|97}{ptr_jugador:05d}.bmp`), que el juego lee como override. Convención de
fotos confirmada por el tutorial de PC Futbolpedia (ej.: puntero 2528 -> j9602528.bmp;
en v5 los punteros >19999 no muestran foto). Este módulo convierte una imagen
cualquiera a ese formato.

Tamaños (MEDIDOS en los contenedores del juego, ver ESCUDO_SIZES): escudo nano 24x32,
mini 48x64, ridi 17x20; foto (minifoto) 32x32.
"""
from __future__ import annotations

import json
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

# ANTI-BOMBA DE DESCOMPRESIÓN (2026-08-16): las imágenes las sube el usuario y un PNG
# de pocos KB puede declarar 100+ megapíxeles; al convertirlo a RGB son cientos de MB de
# RAM por petición. Pillow solo AVISA entre 89 y 178 Mpx (y falla por encima), así que
# aquí se baja el listón a 30 Mpx —muy por encima de cualquier escudo o foto real— y se
# comprueba explícitamente antes de tocar los píxeles.
Image.MAX_IMAGE_PIXELS = 30_000_000


def guard_image(img):
    """Rechaza imágenes desproporcionadas ANTES de decodificarlas."""
    w, h = img.size
    if w * h > Image.MAX_IMAGE_PIXELS or w > 20000 or h > 20000:
        raise ValueError(f"imagen demasiado grande ({w}x{h})")
    return img


_REFDIR = Path(__file__).resolve().parent.parent / "refdata"

# Tamaños MEDIDOS en los contenedores originales (~4.900 escudos de las 8 ediciones de
# v5/6):
#   NANOESC 24×32  (99,5% de las entradas; los 23×31 sueltos son rarezas de Dinamic)
#   MINIESC 48×64  (99,5%)
#   RIDIESC 17×20  (4.900 de 4.900, sin una sola excepción) — ojo, es la CAMISETITA de
#                  las clasificaciones, no el escudo
#   BIGESC         VARIABLE: 160×194 es el más común, luego 164×219 y 164×174. Como el
#                  juego admite los tres, se conserva 164×174, que también es original.
# CORREGIDO 2026-08-20: nano y ridi llevaban 25×32 y 19×21, que no aparecen en NI UNA de
# las imágenes del juego. Nuestra propia
# tabla de PCF7 (`pcf7_image.ESCUDO_SIZES`) ya tenía los buenos.
ESCUDO_SIZES = {"nano": (24, 32), "mini": (48, 64), "ridi": (17, 20), "big": (164, 174)}
PHOTO_SIZE = (32, 32)
BIGFOTO_SIZE = (124, 182)
CAMISA_SIZE = (73, 38)
BANDERA_SIZES = {"big": (30, 20), "mini": (14, 10)}


@lru_cache(maxsize=1)
def _palette() -> list[int]:
    """Paleta fija del juego (768 enteros = 256 colores RGB)."""
    data = json.loads((_REFDIR / "palette_escudo.json").read_text())
    if len(data) < 768:
        data = data + [0] * (768 - len(data))
    return data[:768]


@lru_cache(maxsize=1)
def _palette_image() -> Image.Image:
    pal = Image.new("P", (1, 1))
    pal.putpalette(_palette())
    return pal


# El juego pinta el índice 0 como TRANSPARENTE, así que el negro de un escudo no puede ir
# ahí o el dibujo sale agujereado (unas rayas negras dejarían ver el fondo de la pantalla).
# Dinamic lo resolvió reservando el 0 para el fondo y pintando el negro con el índice 135,
# (22,22,22). Verificado sobre los escudos originales de 5.0 Oro: las cuatro esquinas de
# TODOS son índice 0, y el negro del dibujo es siempre el 135 — en el del Barakaldo, 9.676
# píxeles de casi-negro (sus rayas) frente a 12.011 de fondo. Las herramientas de la
# comunidad hacen lo mismo por otra vía (`-fuzz 15% -fill #101010 -opaque black`).
_NEGRO_VISIBLE = (22, 22, 22)      # índice 135 de la paleta del juego
_UMBRAL_NEGRO = 24                 # por debajo de esto, la cuantización caería en el 0


def _negro_visible(img: "Image.Image", opaco: "Image.Image") -> "Image.Image":
    """Sube a (22,22,22) los negros de las zonas OPACAS, para que no acaben en el índice 0.

    Solo toca lo que era opaco en el original: lo que venía transparente sigue en negro puro
    y el juego lo respeta como fondo. En imágenes sin canal alfa no se llama — ahí un fondo
    negro recortado ES la transparencia y subirlo pintaría un recuadro."""
    from PIL import ImageChops
    r, g, b = img.split()
    # "Casi negro" = LOS TRES canales bajos, o sea el MÁXIMO de los tres por debajo del
    # umbral. Con el mínimo (que es lo que puse primero) entraban todos los colores
    # saturados —un rojo puro es (210,0,0), mínimo 0— y el escudo entero se volvía gris
    # oscuro. Lo destapó la muestra comparativa: el Barça salía negro.
    oscuro = ImageChops.lighter(ImageChops.lighter(r, g), b).point(
        lambda v: 255 if v < _UMBRAL_NEGRO else 0)
    zona = ImageChops.multiply(oscuro, opaco)          # casi-negro Y opaco
    if not zona.getbbox():
        return img
    return Image.composite(Image.new("RGB", img.size, _NEGRO_VISIBLE), img, zona)


def to_game_bmp(image_bytes: bytes, size: tuple[int, int], *, dither: bool = False,
                flat: bool = False, cover: bool = False, encaja: bool = False) -> bytes:
    """Convierte una imagen (PNG/JPG/…) a BMP 256 colores del juego con la paleta fija.
    La transparencia se aplana sobre NEGRO (el juego lo trata como transparente).

    `flat=True` (escudos/banderas: gráficos planos) reduce los **puntitos** que salen al mapear a
    la paleta VGA fija: el ruido de compresión JPEG y los micro-degradados del logo hacen que
    píxeles casi idénticos caigan en 2-3 entradas cercanas de la paleta → moteado. Se aplana ANTES
    de mapear: (1) mediana suave sobre el original (quita motas/bloques JPEG sin comerse el borde),
    (2) reducción a pocos colores (MEDIANCUT) → regiones realmente planas; así cada zona mapea a UNA
    sola entrada de la paleta. Sin dither (los escudos son planos)."""
    img = guard_image(Image.open(BytesIO(image_bytes)))
    opaco = None
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        opaco = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
        base = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(base, img)
    img = img.convert("RGB")
    if flat and opaco is not None:
        img = _negro_visible(img, opaco)
    if flat and encaja and opaco is not None:
        caja = opaco.getbbox()                     # fuera el aire transparente de alrededor
        if caja:
            img, opaco = img.crop(caja), opaco.crop(caja)
    if flat and min(img.size) >= 48 and min(size) >= 48:
        from PIL import ImageFilter               # la mediana solo en los grandes (ver pcf7_image)
        img = img.filter(ImageFilter.MedianFilter(3))
    if cover:
        # FOTOS: mantener la relación de aspecto (recorte "cover" centrado en la cara,
        # ligeramente hacia arriba) en vez de estirar → sin caras estrechas/deformadas.
        img = encuadre_ficha(img, size)
    elif encaja:
        # ESCUDOS: escalar hasta que quepa CONSERVANDO LA PROPORCIÓN y centrar sobre el
        # fondo transparente, en vez de estirar al tamaño exacto. Es lo que hizo Dinamic:
        # sus escudos dejan márgenes variables según la forma de cada uno —el del Zaragoza,
        # estrecho y alto, tiene 8 y 10 px de margen lateral en un lienzo de 48— y estirarlo
        # lo ensanchaba. Comparado escudo a escudo contra los originales.
        from PIL import ImageOps
        from .pcf7_image import _nitido_pequeno
        enc = ImageOps.contain(img, size, Image.LANCZOS)
        if flat:
            enc = _nitido_pequeno(enc, size)
        lienzo = Image.new("RGB", size, (0, 0, 0))
        lienzo.paste(enc, ((size[0] - enc.width) // 2, (size[1] - enc.height) // 2))
        img = lienzo
    else:
        img = img.resize(size, Image.LANCZOS)
    if flat:
        # aplana el resultado (incluye los tonos intermedios que crea el LANCZOS en los bordes)
        img = img.quantize(colors=64, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    q = img.quantize(palette=_palette_image(), dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
    out = BytesIO()
    q.save(out, format="BMP")
    return out.getvalue()


def escudo_set(image_bytes: bytes) -> dict[str, bytes]:
    """Escudo en los cuatro tamaños {nano, mini, ridi, big} como BMP del juego.
    `flat=True`: los escudos son gráficos planos → se aplana el ruido para evitar puntitos.
    `encaja=True`: se conserva la proporción del escudo (Dinamic no los estiraba)."""
    return {name: to_game_bmp(image_bytes, size, flat=True, encaja=True)
            for name, size in ESCUDO_SIZES.items()}


def _una_foto(image_bytes: bytes, size, dither: bool, fondo: str = "blanco") -> bytes:
    """Una foto al tamaño pedido. Si la imagen viene RECORTADA sobre transparente —los
    retratos recortados— se le pone antes el fondo de metal cepillado y se reencuadra como las
    del juego (ver `photo_bg`). Las fotos de prensa ya traen su fondo y no se tocan."""
    from . import photo_bg
    try:
        src = guard_image(Image.open(BytesIO(image_bytes)))
        img = None
        if photo_bg.tiene_alfa(src):
            img = photo_bg.con_fondo(src, size, fondo)
        elif fondo != "blanco":
            sin = quitar_fondo_blanco(src)          # fondo blanco → el elegido, como los retratos recortados
            if sin is not None:
                img = ficha_con_fondo(sin, size, fondo)
        if img is not None:
            buf = BytesIO()
            img.save(buf, "PNG")
            return to_game_bmp(buf.getvalue(), size, dither=dither)
    except Exception:  # noqa: BLE001  (cualquier rareza → camino de siempre)
        pass
    return to_game_bmp(image_bytes, size, dither=dither, cover=True)


# La minifoto del juego es de 32x32. La fuente que se guarda en la sesión solo sirve para
# generarla, así que no tiene sentido arrastrar el original: un retrato a tamaño completo pesa
# cientos de veces lo que se va a pintar. Medido en un mod real de
# PCF7: 12.102 minifotos ocupaban 1,79 GB, y con eso el proceso que lo tenía cargado se
# pasaba varios segundos en cada recogida de basura y dejaba de responder.
#
# 128 px es cuatro veces el lado final: sobra para que el reescalado salga limpio y deja la
# fuente en ~20 KB. Se conserva el alfa, que es lo que permite ponerle después el fondo.
MINI_SRC_MAX = 128


def con_fondo_si_transparente(png: bytes, size=BIGFOTO_SIZE, fondo="blanco") -> bytes:
    """Si la imagen viene RECORTADA sobre transparente (los retratos recortados), la compone sobre
    el fondo del juego y devuelve un PNG ya opaco. Si no, la deja igual.

    Se aplica al GUARDAR la foto, no solo al escribir el fichero del juego. Antes el fondo se
    ponía únicamente al generar el BMP/GIF final, así que lo que quedaba en el mod —y lo que
    enseñaba la web— era el retrato recortado con su transparencia: en la ficha se veía el fondo
    de la página a través del jugador, y al aplanarlo salía negro."""
    if not png:
        return png
    from . import photo_bg
    try:
        src = guard_image(Image.open(BytesIO(png)))
        if photo_bg.tiene_alfa(src):
            img = photo_bg.con_fondo(src, size, fondo)
        else:
            # Fotos de prensa con fondo BLANCO. Con el fondo
            # «blanco» (el genérico, por defecto) se dejan tal cual: cero coste. Con otro fondo
            # se quita el blanco y van sobre el mismo que los retratos recortados, para que toda la
            # plantilla luzca igual (2026-09-06). Las que traen un fondo real (grada,
            # campo) se dejan siempre como están.
            if isinstance(fondo, str) and fondo == "blanco":
                return png
            # MISMO ENCUADRE que con «blanco» (17-sep-2026: «¿por qué se ven distintas
            # las fotos en blanco y en azul?»): antes se quitaba el blanco de la foto entera y
            # luego se reencuadraba de otra forma, y la cara cambiaba de tamaño según el fondo.
            # Ahora se encuadra primero, como la de fondo blanco, y solo se cambia el fondo.
            from .photo_bg import fondo_ficha
            enmarcada = encuadre_ficha(src.convert("RGB"), size)
            sin = quitar_fondo_blanco(enmarcada)
            if sin is None:
                return png
            img = fondo_ficha(size, fondo)
            img.alpha_composite(sin.convert("RGBA").resize(size))
            img = img.convert("RGB")
        out = BytesIO()
        # SIN `optimize`: este PNG es un PASO INTERMEDIO —de aquí sale siempre el JPEG de la
        # ficha o el BMP del juego, nunca se guarda tal cual—, así que apretar el zlib solo
        # cuesta tiempo. Medido con una foto de 124×182: 5,4 ms con `optimize` y 0,8 ms sin él,
        # con EL MISMO tamaño (una foto no se comprime mejor por insistir). Era el 11 % del
        # tiempo de una actualización completa. Los píxeles no
        # cambian: lo que llega al juego es idéntico.
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:  # noqa: BLE001  (si no se puede abrir, se deja como está)
        return png


def quitar_fondo_blanco(im: "Image.Image") -> "Image.Image | None":
    """Foto de prensa con FONDO PLANO CLARO (el blanco de las fotos de prensa) →
    RGBA con ese fondo transparente. None si no tiene ese fondo (fotos con grada, campo…), que
    se dejan como están.

    Cómo: las cuatro esquinas tienen que ser casi iguales y claras; desde el borde se inunda todo
    lo que se parece a ese color (así el blanco de una camiseta o de los ojos, que no toca el
    borde, se queda). El borde de la máscara se come 1 px y se suaviza, para que no quede el halo
    blanco alrededor del pelo."""
    from PIL import ImageChops, ImageDraw, ImageFilter
    rgb = im.convert("RGB")
    w, h = rgb.size
    if w < 40 or h < 40:
        return None
    px = rgb.load()
    # El color del fondo se lee ARRIBA (esquinas superiores y un poco más abajo por los lados):
    # en un busto los hombros llegan hasta las esquinas de abajo, así que esas no valen.
    muestras = [px[0, 0], px[w - 1, 0], px[0, h // 8], px[w - 1, h // 8]]
    fondo = tuple(sum(c[i] for c in muestras) // 4 for i in range(3))
    if min(fondo) < 200:                                    # no es un fondo claro
        return None
    if max(abs(c[i] - fondo[i]) for c in muestras for i in range(3)) > 16:
        return None                                         # el borde de arriba no es plano
    # diferencia con el color del fondo → imagen "L" donde 0 = igual al fondo
    dif = ImageChops.difference(rgb, Image.new("RGB", rgb.size, fondo)).convert("L")
    # La inundación (`floodfill` es Python puro, píxel a píxel) va a MEDIA resolución: la
    # máscara se calcula sobre ~128-200 px de lado y se vuelve a ampliar con interpolación,
    # que además deja el borde suave. A tamaño completo eran ~100 ms por foto y en un
    # actualización completa de PCF7 sumaba una hora entera.
    k = 2 if min(w, h) >= 160 else 1
    dw, dh = w // k, h // k
    dif_s = dif.resize((dw, dh), Image.BILINEAR) if k > 1 else dif
    # Inundar desde el borde lo que se parece al fondo. En vez de `ImageDraw.floodfill` (Python
    # píxel a píxel, ~50 ms) se hace por DILATACIONES en C: la semilla es el marco de 1 px, y en
    # cada vuelta crece un píxel (MaxFilter 3×3) pero solo sobre los píxeles candidatos a fondo
    # (multiply). Converge en tantas vueltas como píxeles tenga que recorrer (~100 a esta
    # resolución) y cada vuelta cuesta microsegundos.
    cand = dif_s.point(lambda v: 255 if v <= 34 else 0)
    # Semilla: el borde de ARRIBA y los laterales hasta el 60 % de la altura. El de abajo NO: en
    # un busto es camiseta, y una camiseta con blanco que toca el canto (rayas, cuello) se
    # inundaba como si fuera fondo —con fondo propio se veía la imagen a través de las rayas
    # (17-sep-2026)—. El fondo real baja por los lados hasta los hombros.
    seed = Image.new("L", (dw, dh), 0)
    dib = ImageDraw.Draw(seed)
    dib.line((0, 0, dw - 1, 0), fill=255)
    alto = max(1, int(dh * 0.6))
    dib.line((0, 0, 0, alto), fill=255)
    dib.line((dw - 1, 0, dw - 1, alto), fill=255)
    seed = ImageChops.multiply(seed, cand)
    for _ in range(max(dw, dh) * 2):
        grown = ImageChops.multiply(seed.filter(ImageFilter.MaxFilter(3)), cand)
        if ImageChops.difference(grown, seed).getbbox() is None:
            break
        seed = grown
    inund = seed
    if inund.getbbox() is None:
        return None
    cubierto = sum(inund.histogram()[255:]) / float(dw * dh)
    if cubierto < 0.08 or cubierto > 0.92:                  # ni fondo apreciable ni foto vacía
        return None
    alfa = ImageChops.invert(inund)
    alfa = alfa.filter(ImageFilter.MinFilter(3))            # 1 px menos: fuera el halo
    if k > 1:
        alfa = alfa.resize((w, h), Image.BILINEAR)
    alfa = alfa.filter(ImageFilter.GaussianBlur(0.6))
    out = rgb.convert("RGBA")
    out.putalpha(alfa)
    return out


def ficha_con_fondo(retrato: "Image.Image", size: tuple[int, int],
                    fondo: str = "metal") -> "Image.Image":
    """Retrato RGBA (ya sin fondo) → ficha: se encuadra como cualquier foto (aire fuera, cara
    al ancho, anclado arriba) y se compone sobre el fondo elegido (metal cepillado o blanco)."""
    from PIL import ImageOps
    from .photo_bg import fondo_ficha
    fg = retrato.convert("RGBA")
    caja = fg.split()[-1].getbbox()
    if caja:
        fg = fg.crop(caja)
    fg = ImageOps.fit(fg, size, Image.LANCZOS, centering=(0.5, 0.0))
    lienzo = fondo_ficha(size, fondo)
    lienzo.alpha_composite(fg)
    return lienzo.convert("RGB")


def _aire_uniforme(im: "Image.Image") -> tuple[int, int, int, int] | None:
    """Caja del sujeto cuando la foto trae AIRE uniforme alrededor (el fondo blanco de las
    fotos de prensa, o un color plano). Devuelve None si no hay borde uniforme
    o si recortarlo no cambia nada apreciable."""
    from PIL import ImageChops
    w, h = im.size
    if w < 40 or h < 40:
        return None
    px = im.load()
    esquinas = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    fondo = tuple(sum(c[i] for c in esquinas) // 4 for i in range(3))
    if max(abs(c[i] - fondo[i]) for c in esquinas for i in range(3)) > 18:
        return None                                     # las esquinas no coinciden: no es aire
    dif = ImageChops.difference(im, Image.new("RGB", im.size, fondo)).convert("L")
    caja = dif.point(lambda v: 255 if v > 28 else 0).getbbox()
    if not caja:
        return None
    x0, y0, x1, y1 = caja
    if (x1 - x0) > w * 0.96 and (y1 - y0) > h * 0.96:
        return None                                     # el sujeto ya llena el marco
    mx, my = round(w * 0.03), round(h * 0.03)           # un poco de aire, que no toque el borde
    return (max(0, x0 - mx), max(0, y0 - my), min(w, x1 + mx), min(h, y1 + my))


def _cabeza(im: "Image.Image") -> tuple[int, int, int] | None:
    """(x0, x1, y0) de la CABEZA en un retrato con fondo plano, o None si no se puede medir.

    Se mide por filas: el ancho del sujeto crece despacio mientras es la cabeza y se DISPARA
    al llegar a los hombros. La cabeza es el tramo de arriba hasta ese salto; su ancho, el
    mayor de ese tramo (pómulos/orejas). Sin fondo plano no hay sujeto que medir."""
    from PIL import ImageChops
    w, h = im.size
    if w < 40 or h < 40:
        return None
    px = im.load()
    # El fondo se toma de las esquinas de ARRIBA, no de las cuatro: en un retrato los hombros
    # llegan a las esquinas de abajo (algunas fotos de prensa las tienen negras) y la
    # media de las cuatro daba un gris que no era el fondo de nada.
    esquinas = [px[x, y] for y in (0, 1, 2) for x in (0, 1, 2, w - 3, w - 2, w - 1)]
    fondo = tuple(sum(c[i] for c in esquinas) // len(esquinas) for i in range(3))
    if max(abs(c[i] - fondo[i]) for c in esquinas for i in range(3)) > 30:
        return None                                     # fondo no uniforme: no se puede medir
    mask = ImageChops.difference(im, Image.new("RGB", im.size, fondo)).convert("L") \
        .point(lambda v: 255 if v > 28 else 0)
    caja = mask.getbbox()
    if not caja:
        return None
    bx0, by0, bx1, by1 = caja
    alto = by1 - by0
    if alto < 20:
        return None
    # El recorrido va por FILAS sobre los bytes crudos de la máscara (`find`/`rfind` en C): a
    # mano, píxel a píxel, son 100.000 vueltas de Python por foto y esto corre también al armar
    # la descarga, con miles de fotos por mod.
    crudo = mask.tobytes()
    anchos, centros = [], []
    for y in range(by0, by1):
        fila = crudo[y * w:(y + 1) * w]
        xs0, xs1 = fila.find(255), fila.rfind(255)
        anchos.append(0 if xs0 < 0 else xs1 - xs0 + 1)
        centros.append(None if xs0 < 0 else (xs0 + xs1) / 2)
    # La CABEZA es el tramo de arriba hasta el CUELLO, que es donde el ancho cae claramente por
    # debajo del máximo alcanzado (pómulos/orejas). Buscar en cambio el "salto" de los hombros
    # se pasaba de largo: cuando se dispara ya se ha comido la rampa del hombro y la cabeza
    # salía medio marco más ancha de lo que es.
    pico = 0
    cuello = None
    for i, a in enumerate(anchos):
        pico = max(pico, a)
        if pico >= 20 and a < pico * 0.78 and i > 4:
            cuello = i
            break
    if cuello is None or pico < 16:
        return None                                     # sin cuello visible: no se puede medir
    banda = [c for c in centros[:cuello] if c is not None]
    if len(banda) < 8:
        return None
    cx = sorted(banda)[len(banda) // 2]
    return (round(cx - pico / 2), round(cx + pico / 2), by0)


# Proporciones MEDIDAS sobre las fotos originales de Dinamic (Barcelona de PCF7, rejilla sobre
# `DBDAT/BIGFOTO`): en la ficha la cabeza ocupa el 36% del ancho y la coronilla queda al 5% del
# alto —es un plano de busto, con hombros y aire—; la minifoto de 32×32 es en cambio un primer
# plano, con la cabeza al 70% del ancho y la coronilla casi tocando el borde.
# ELEGIDO (17-sep-2026) entre cuatro demos con jugadores reales: en la ficha la
# cabeza al 66% del ancho («se ve mucho cuerpo y la cara se ve pequeña» con el 36% de Dinamic —sus
# fotos traían busto con hombros; las de hoy son primeros planos—). La minifoto, el 70% medido.
_ENCUADRE_FICHA = (0.66, 0.08)      # (ancho de la cabeza / ancho, coronilla / alto)
_ENCUADRE_MINI = (0.70, 0.02)


def encuadre_ficha(im: "Image.Image", size: tuple[int, int]) -> "Image.Image":
    """Encaja una foto en el hueco del juego SIN deformarla y con el ENCUADRE de Dinamic.

    Antes se recortaba el aire de alrededor y se hacía un "cover" anclado arriba, y con eso el
    rostro se comía el marco: en la ficha salía un primerísimo plano cortado por el cuello, muy
    lejos del busto con hombros de las fotos del juego (foro, 13-sep-2026: «el rostro
    es muy grande para la casilla de foto del juego»).

    Ahora se MIDE la cabeza (`_cabeza`) y se coloca en la proporción del juego: se escala para
    que tenga el ancho que le toca y se sitúa la coronilla a su altura. Lo que falte por abajo
    o por los lados se completa estirando el borde de la foto —que en un retrato de prensa es
    el fondo, así que no se nota—. Si no hay fondo plano que permita medir la cabeza, se
    conserva el encuadre de antes."""
    from PIL import ImageOps
    im = im.convert("RGB")
    W, H = size
    cab = _cabeza(im)
    if cab:
        ancho_obj, alto_obj = _ENCUADRE_MINI if H < W * 1.3 else _ENCUADRE_FICHA
        x0, x1, y0 = cab
        k = (W * ancho_obj) / max(1, x1 - x0)
        # …pero sin quedarse corto: las fotos de hoy  son primeros planos casi
        # cuadrados y no traen busto que enseñar, así que apretar hasta el 36% de Dinamic dejaba
        # franjas de fondo a los lados y media ficha de relleno. El suelo es que la foto cubra al
        # menos el ancho del hueco; con una fuente que SÍ trae cuerpo manda el objetivo.
        k = max(k, W / im.width)
        if 0.05 < k < 8:
            esc = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))),
                            Image.LANCZOS)
            dx = round(W / 2 - (x0 + x1) / 2 * k)
            dy = round(H * alto_obj - y0 * k)
            return _pega_extendiendo(esc, size, dx, dy)
    caja = _aire_uniforme(im)
    if caja:
        im = im.crop(caja)
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.0))


def _pega_extendiendo(im: "Image.Image", size: tuple[int, int], dx: int, dy: int) -> "Image.Image":
    """Pega `im` en un lienzo de `size` en (dx, dy) y rellena lo que quede fuera ESTIRANDO la
    fila o columna del borde. En un retrato de prensa el borde es el fondo, así que el relleno
    pasa desapercibido; abajo, donde el borde es la camiseta, se lee como que sigue el cuerpo."""
    from PIL import ImageFilter
    W, H = size
    lienzo = Image.new("RGB", size)
    if dx > 0:                                          # falta por la izquierda
        lienzo.paste(im.crop((0, 0, 1, im.height)).resize((dx, im.height)), (0, dy))
    if dx + im.width < W:                               # …y por la derecha
        lienzo.paste(im.crop((im.width - 1, 0, im.width, im.height))
                     .resize((W - dx - im.width, im.height)), (dx + im.width, dy))
    lienzo.paste(im, (dx, dy))
    if dy > 0:                                          # falta por arriba
        lienzo.paste(lienzo.crop((0, dy, W, dy + 1)).resize((W, dy)), (0, 0))
    fin = dy + im.height
    if fin < H:
        # Por abajo NO se repite una fila suelta: el ruido de esa única línea se convertía en
        # RAYAS verticales sobre la camiseta. Se estira una franja de varias filas y se le pasa
        # un desenfoque, con lo que el relleno se lee como que el cuerpo sigue hacia abajo.
        franja = max(2, min(8, im.height // 12))
        relleno = lienzo.crop((0, fin - franja, W, fin)).resize((W, H - fin), Image.BILINEAR)
        lienzo.paste(relleno.filter(ImageFilter.GaussianBlur(1.6)), (0, fin))
    return lienzo


# Hasta esta proporción de alto/ancho, la foto ENTRA ENTERA en la minifoto; por encima se
# recorta a primer plano. Las fotos
# cuadradas caben enteras sin sacrificar nada. En las verticales, encajarlas dejaría franjas,
# que es lo que había que evitar.
_MINI_ENTERA_HASTA = 1.25


def _escala_para_caber(im: "Image.Image", lado: int) -> "Image.Image":
    """La imagen escalada para LLENAR el cuadrado, ampliándola si viene pequeña.

    Antes se usaba `thumbnail`, que solo REDUCE: una foto hecha a mano de 32×32 —las de toda la
    vida— se quedaba a su tamaño en medio de un lienzo de 128 y acababa ocupando la cuarta parte
    del marco. Medido: una cara que en el original ocupaba el 50% del ancho salía al 12%
    (foro, 22-sep-2026: «que se ajuste sola a marco completo y no parcial»).

    Al ampliar se usa NEAREST cuando el factor es un número entero, que es justo el caso de esas
    fotos antiguas (32→128 es ×4): así los píxeles se duplican tal cual y el dibujo no se
    emborrona. Para cualquier otro factor, LANCZOS."""
    if im.width <= 0 or im.height <= 0:
        return im
    f = min(lado / im.width, lado / im.height)
    if f == 1:
        return im
    ancho, alto = max(1, round(im.width * f)), max(1, round(im.height * f))
    entero = f > 1 and abs(f - round(f)) < 1e-6
    return im.resize((ancho, alto), Image.NEAREST if entero else Image.LANCZOS)


def fuente_de_minifoto(png: bytes, lado: int = 128) -> bytes:
    """La imagen de la que sale la MINIFOTO, en un CUADRADO.

    Si la foto ya viene casi cuadrada entra ENTERA (hasta `_MINI_ENTERA_HASTA`); si es muy
    vertical se recorta a primer plano con la cara centrada (`_ENCUADRE_MINI`, 70% del ancho).

    Por qué las dos cosas. Recortar SIEMPRE dejaba la mini cortada —se iba
    la coronilla o la barbilla— y eso es lo que se veía al subir una foto: la grande
    salía entera y la pequeña no (foro, 20-sep-2026; un usuario ya lo había dicho de las
    fotos «seccionadas a la altura de la mandíbula»). Encajarla SIEMPRE tampoco vale: con un
    retrato vertical vuelven las franjas a los lados, que es justo lo que se arregló el
    17-sep-2026 en PCF7 (entonces se encajaba la ficha entera de 124×182
    en el cuadrado de 32×32). Como el import trae las fotos cuadradas, el reparto sale gratis:
    lo normal es que entre entera y solo se recorta lo que no cabe de otra manera.

    Lo que sobra a los lados NO se rellena de negro: se estira el borde (`_pega_extendiendo`),
    que en un retrato es el fondo y pasa desapercibido. Un cuadrado de 128 px deja al conversor
    reducir a 32×32 con margen."""
    if not png:
        return png
    im = guard_image(Image.open(BytesIO(png)))
    if im.height <= im.width * _MINI_ENTERA_HASTA:
        entera = _escala_para_caber(im.convert("RGB").copy(), lado)
        cuadro = _pega_extendiendo(entera, (lado, lado),
                                   (lado - entera.width) // 2, (lado - entera.height) // 2)
    else:
        cuadro = encuadre_ficha(im, (lado, lado))
    out = BytesIO()
    cuadro.save(out, "PNG")
    return out.getvalue()


def fuente_de_ficha(png: bytes) -> bytes:
    """Deja la foto de un jugador al tamaño en el que el juego la va a pintar.

    Se guardaba tal como llegaba de la fuente —una foto grande o un retrato
    recortado— para poder regenerar el recorte si algún día cambiaba el encuadre. Sale caro: la
    ficha del juego mide 124×182, así que se guardaba dos veces y media la resolución que se
    llega a dibujar, y una segunda copia aparte para la minifoto de 32×32. En un mod real eran
    762 MB de fotos sobre 810 MB de mod.

    De esta imagen salen LAS DOS: la ficha (a tamaño exacto) y la minifoto (reduciéndola).
    Calidad 88 porque va a JPEG y de aquí se cuantiza a la paleta del juego; por debajo se
    empiezan a ver los bloques en las caras."""
    if not png:
        return png
    try:
        im = guard_image(Image.open(BytesIO(png)))
        if im.size == BIGFOTO_SIZE and (im.format or "").upper() == "JPEG":
            return png                                   # ya está como la queremos
        redimensionada = im.size != BIGFOTO_SIZE
        im = im.convert("RGB")
        if redimensionada:
            im = encuadre_ficha(im, BIGFOTO_SIZE)
        out = BytesIO()
        im.save(out, format="JPEG", quality=88, optimize=True)
        # Quedarse con el original solo si NO había que reencuadrar: una foto de prensa
        # pequeña (100×130) pesa menos que su versión a 124×182, y devolverla dejaba la ficha
        # guardada con el tamaño equivocado. El peso no puede mandar sobre el tamaño.
        if redimensionada or out.tell() < len(png):
            return out.getvalue()
        return png
    except Exception:  # noqa: BLE001  (si no se puede abrir, se deja como está)
        return png


def reduce_para_minifoto(png: bytes, maximo: int = MINI_SRC_MAX) -> bytes:
    """Deja la fuente de una minifoto en un tamaño razonable. Si ya es pequeña, no la toca.

    `maximo` permite apretar más al recomprimir mods viejos: la minifoto que pinta el juego es
    de 32×32, así que con 64 px de fuente sobra y ocupa la cuarta parte."""
    if not png:
        return png
    try:
        im = guard_image(Image.open(BytesIO(png)))
        if max(im.size) <= maximo:
            return png
        im = im.copy()
        im.thumbnail((maximo, maximo), Image.LANCZOS)
        out = BytesIO()
        im.save(out, format="PNG", optimize=True)
        return out.getvalue() if out.tell() < len(png) else png
    except Exception:  # noqa: BLE001  (si no se puede abrir, se deja como está)
        return png


def photo_set(image_bytes: bytes, mini_bytes: bytes | None = None,
              fondo="blanco", compuesta: bytes | None = None) -> dict[str, bytes]:
    """Foto de jugador: minifoto 32x32 + foto grande 124x182.

    Las dos pueden venir de FUENTES DISTINTAS, que es como quedan mejor: una foto de ficha
    (que viene ya encuadrada y con su fondo) y, para la minifoto, un retrato recortado
    (centrado, aguanta mucho mejor la bajada a 32×32). Con `mini_bytes` a None
    salen las dos de la misma imagen."""
    return {"big": _una_foto(image_bytes, BIGFOTO_SIZE, True, fondo),
            "mini": _una_foto(mini_bytes or image_bytes, PHOTO_SIZE, False, fondo)}


def silueta_png(size=BIGFOTO_SIZE) -> bytes:
    """Silueta neutra de jugador, DIBUJADA AQUÍ (sin red).

    Es la red de seguridad del import: al recolocar una plantilla, el hueco que se queda sin
    foto mostraría la del jugador que lo ocupaba en el fichero de fábrica, que es OTRA PERSONA
    (fallo del foro, 30-ago-2026).
    Antes se descargaba y, sin red, la protección se caía entera y en silencio. Dibujada, no
    puede fallar.
    """
    from . import photo_bg
    w, h = size
    fondo = photo_bg.brushed_metal(w, h).convert("RGB")
    d = ImageDraw.Draw(fondo)
    gris = (108, 112, 118)
    cab = h * 0.30                      # diámetro de la cabeza
    cx = w / 2
    d.ellipse((cx - cab / 2, h * 0.16, cx + cab / 2, h * 0.16 + cab), fill=gris)
    # hombros: elipse ancha que sale por abajo del encuadre, como los bustos del juego
    d.ellipse((cx - w * 0.42, h * 0.56, cx + w * 0.42, h * 1.35), fill=gris)
    buf = BytesIO()
    fondo.save(buf, "PNG")
    return buf.getvalue()


def silueta_photo_set() -> dict[str, bytes]:
    """`photo_set` de la silueta neutra, lista para asignar a un jugador sin foto."""
    png = silueta_png()
    return {"big": to_game_bmp(png, BIGFOTO_SIZE, dither=True),
            "mini": to_game_bmp(silueta_png(PHOTO_SIZE), PHOTO_SIZE, dither=False)}


def photo_bmp(image_bytes: bytes) -> bytes:
    """Foto de jugador (minifoto 32x32) como BMP del juego."""
    return to_game_bmp(image_bytes, PHOTO_SIZE, cover=True)


def camisa_bmp(image_bytes: bytes) -> bytes:
    """Camiseta/equipación (73x38) como BMP del juego."""
    return to_game_bmp(image_bytes, CAMISA_SIZE)


def bandera_set(image_bytes: bytes) -> dict[str, bytes]:
    """Bandera de país en los dos tamaños {big 30x20, mini 14x10}. Plana (sin puntitos)."""
    return {name: to_game_bmp(image_bytes, size, flat=True) for name, size in BANDERA_SIZES.items()}


def game_bmp_to_png(bmp_bytes: bytes, transparent: bool = False) -> bytes:
    """BMP del juego -> PNG (para previsualizar en el navegador), escalado x4 nítido.
    `transparent`: hace el fondo NEGRO (índice 0 de la paleta, que el juego trata como
    transparente) transparente de verdad — para ESCUDOS, así no salen con recuadro negro."""
    img = guard_image(Image.open(BytesIO(bmp_bytes))).convert("RGB")
    if transparent:
        # el negro puro (0,0,0) = índice 0 = fondo transparente del juego. Se hace ANTES
        # del escalado (menos píxeles) y con NEAREST el alpha se conserva nítido.
        img = img.convert("RGBA")
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, _ = px[x, y]
                if r == 0 and g == 0 and b == 0:
                    px[x, y] = (0, 0, 0, 0)
    img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def dm_blob_to_png(blob: bytes, transparent: bool = False) -> bytes:
    """Imagen DM de un contenedor original (BMP sin paleta) -> PNG con la paleta del juego.
    `transparent`: fondo negro transparente (escudos)."""
    from houdini_engine.formats import imagenes_pkf
    return game_bmp_to_png(imagenes_pkf.dm_to_bmp(blob, _palette()), transparent=transparent)
