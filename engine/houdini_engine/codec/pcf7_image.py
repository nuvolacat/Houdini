"""Códec de imágenes de PCF 7 / PC Calcio 7+.

Como v5/6, el juego lee **BMP de 256 colores sueltos** en `DBDAT\\<carpeta>\\` como
override (sin repackear el PKF). PERO la paleta NO es la de v5/6: PCF7 usa 2 paletas
fijas propias (verificado, difieren en 19 colores), extraídas de las BMP del juego:
- **main**: escudos (miniesc/nanoesc/ridiesc/bigesc) y fotos (minifoto/bigfoto).
- **banderas**: banderas + minibandas.
(Las fotos de estadio, 320×240, llevan paleta propia por imagen → no cuantizamos a
una fija; se convierten con su propia paleta óptima.)

Naming de fichero suelto (confirmado por el mod del juego):
- escudo mini  `MINIESC\\eq98<tid:04d>.bmp`  (48×64)
- escudo nano  `NANOESC\\eq98<tid:04d>.bmp`  (24×32)
- escudo ridi  `RIDIESC\\eq98<tid:04d>.bmp`
- minifoto     `MINIFOTO\\J98<ptr:05d>.bmp`  (32×32)
- bandera      `BANDERAS\\ba96<pais:04d>.bmp`(30×20)
- estadio      `ESTADIO\\eq98<tid:04d>.bmp`  (320×240)
BIGFOTO / BIGESC / CAMISAS: la ruta suelta existe pero el naming exacto se confirma
en la VM (se concatena en runtime, como las fotos de PCF4).
"""
from __future__ import annotations

import json
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image

_REFDIR = Path(__file__).resolve().parent.parent / "refdata"

# tamaños confirmados en las BMP del juego/mod
ESCUDO_SIZES = {"mini": (48, 64), "nano": (24, 32), "ridi": (17, 20)}
MINIFOTO_SIZE = (32, 32)
BANDERA_SIZE = (30, 20)
# 14×10, MEDIDO en los contenedores del juego (banderas.pak 30×20 · miniband.pak
# 14×10, en PCF7, 2000 y 2001). Estaba puesto a 30×20 y no lo usaba nadie.
MINIBAND_SIZE = (14, 10)
ESTADIO_SIZE = (320, 240)


@lru_cache(maxsize=2)
def _palette(name: str) -> list[int]:
    data = json.loads((_REFDIR / f"pcf7_palette_{name}.json").read_text())
    return (data + [0] * 768)[:768]


@lru_cache(maxsize=2)
def _palette_image(name: str) -> Image.Image:
    pal = Image.new("P", (1, 1))
    pal.putpalette(_palette(name))
    return pal


@lru_cache(maxsize=2)
def _face_palette(name: str):
    """(paleta_subconjunto, lut256) para cuantizar FOTOS sin verdes/azules VÍVIDOS.
    La paleta `main` tiene 13 verdes puros (y azules vívidos) que las fotos ORIGINALES del
    juego NUNCA usan; al cuantizar fotos reales (fondos, brillos, ruido JPEG) el mapeo mete
    píxeles ahí → los 'píxeles verdes' de las caras. Restringimos el conjunto candidato a los
    índices 'de cara' y remapeamos al índice REAL (la paleta completa se conserva en el BMP)."""
    pal = _palette(name)
    full = [(pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]) for i in range(256)]

    def ok(c):
        r, g, b = c
        # excluir cualquier color donde el VERDE domine, por poco que sea: las caras nunca
        # son verde-dominantes. El umbral bajó de 20 a 6 el 2026-08-20 al ver la minifoto
        # AMPLIADA: con 20 aún quedaba un 0,26% de píxeles con tinte verde —invisibles a
        # tamaño real, pero puntitos claros al agrandarla—. Con 6 son 0,00% y solo se
        # pierden 5 de los 173 colores disponibles.
        if g >= max(c) and (g - max(r, b)) > 6:
            return False
        if b >= max(c) and (b - max(r, g)) > 55:   # azul vívido (fondos)
            return False
        return True

    allowed = [i for i in range(256) if ok(full[i])]
    flat: list[int] = []
    for i in allowed:
        flat += list(full[i])
    sub = Image.new("P", (1, 1))
    sub.putpalette((flat + [0] * 768)[:768])
    lut = bytes(allowed[i] if i < len(allowed) else 0 for i in range(256))
    return sub, lut


def to_game_bmp(image_bytes: bytes, size: tuple[int, int], *,
                palette: str = "main", dither: bool = False,
                flatten=(0, 0, 0), flat: bool = False, cover: bool = False,
                face: bool = False, encaja: bool = False) -> bytes:
    """Convierte una imagen a BMP 256 colores con la paleta fija de PCF7 (`palette`).
    La transparencia se aplana sobre `flatten` (por defecto negro = transparente).
    `flat=True` (escudos/banderas): aplana ruido/JPEG antes de mapear para evitar puntitos
    (mediana suave + MEDIANCUT → regiones planas). Ver detalle en `codec/image.py`."""
    src = Image.open(BytesIO(image_bytes))
    alpha = None
    if src.mode in ("RGBA", "LA", "P"):
        src = src.convert("RGBA")
        alpha = src.getchannel("A")
    img = src.convert("RGB")
    if flat and encaja and alpha is not None:
        # FUERA EL AIRE transparente de alrededor: los escudos que sube la gente (139×181 con
        # margen) salían más pequeños que los de Dinamic, que llenan el lienzo.
        caja = alpha.point(lambda v: 255 if v >= 128 else 0).getbbox()
        if caja:
            img, alpha = img.crop(caja), alpha.crop(caja)
    if flat and min(img.size) >= 48 and min(size) >= 48:
        # la mediana quita el moteado JPEG en el escudo grande; en los pequeños (24×32) solo
        # emborrona (foro, 7-sep-2026: «salen borrosos» en la parrilla de elegir equipo)
        from PIL import ImageFilter
        img = img.filter(ImageFilter.MedianFilter(3))
    if cover:
        # FOTOS: conservar aspecto (recorte "cover" centrado en la cara) en vez de estirar.
        from .image import encuadre_ficha
        img = encuadre_ficha(img, size)
    elif encaja:
        # ESCUDOS: conservar la proporción y centrar (ver el porqué en `codec/image.py`).
        from PIL import ImageOps
        enc = ImageOps.contain(img, size, Image.LANCZOS)
        if flat:
            enc = _nitido_pequeno(enc, size)
        pos = ((size[0] - enc.width) // 2, (size[1] - enc.height) // 2)
        lienzo = Image.new("RGB", size, flatten)
        lienzo.paste(enc, pos)
        img = lienzo
        if alpha is not None:
            # el alfa tiene que seguir EXACTAMENTE la misma geometría que la imagen, o la
            # máscara recortaría por donde no toca
            ea = ImageOps.contain(alpha, size, Image.LANCZOS)
            ma = Image.new("L", size, 0)
            ma.paste(ea, pos)
            alpha = ma
    else:
        img = img.resize(size, Image.LANCZOS)
        if alpha is not None:
            alpha = alpha.resize(size, Image.LANCZOS)
    if alpha is not None:
        # UMBRAL de alpha: borde DURO (opaco o transparente) → sin halo de anti-aliasing.
        # Los píxeles < umbral se pintan del color `flatten` (blanco en PCF7 = transparente),
        # y al recortar la preview quedan limpios (no quedan medios-blancos).
        mask = alpha.point(lambda v: 255 if v >= 128 else 0)
        base = Image.new("RGB", size, flatten)
        base.paste(img, (0, 0), mask)
        img = base
        if flat and tuple(flatten) == (0, 0, 0):
            # El negro del DIBUJO no puede acabar en el índice 0, que el juego pinta
            # transparente: el escudo saldría agujereado. Misma convención que en v5/6 —
            # verificado sobre 60 escudos originales de PCF7: sus 240 esquinas son índice 0
            # y el negro del dibujo es el MISMO índice 135, (22,22,22), con 7.402 píxeles.
            from .image import _negro_visible
            img = _negro_visible(img, mask)
    if flat:
        img = img.quantize(colors=64, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    dmode = Image.FLOYDSTEINBERG if dither else Image.NONE
    if face:
        # cuantizar contra el subconjunto 'de cara' (sin verdes/azules vívidos) y remapear
        # los índices al índice REAL de la paleta completa → 0 speckles verdes en las fotos.
        sub, lut = _face_palette(palette)
        q = img.quantize(palette=sub, dither=dmode)
        q = Image.frombytes("P", q.size, q.tobytes().translate(lut))
        q.putpalette(_palette(palette))
    else:
        q = img.quantize(palette=_palette_image(palette), dither=dmode)
    out = BytesIO()
    q.save(out, format="BMP")
    return out.getvalue()



def _nitido_pequeno(img, size):
    """Escudo reducido a tamaño pequeño: nitidez y algo más de color, para que a 24×32 se lea
    como los que pixeló Dinamic (bordes marcados y colores planos) y no como un borrón gris.
    Comparado contra los originales de PCF7 escudo a escudo (7-sep-2026)."""
    from PIL import ImageEnhance, ImageFilter
    w = min(size)
    if w > 64:
        return img
    fuerte = w <= 32
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=140 if fuerte else 90, threshold=0))
    img = ImageEnhance.Color(img).enhance(1.35 if fuerte else 1.15)
    return ImageEnhance.Contrast(img).enhance(1.15 if fuerte else 1.06)


def escudo_set(image_bytes: bytes) -> dict[str, bytes]:
    """Escudo en {mini, nano, ridi} como BMP del juego. Fondo NEGRO (índice 0): es la convención
    de los escudos originales de PCF7 (sus 4 esquinas son negro puro = transparente en juego).
    Con blanco salía un recuadro blanco opaco en el juego.
    `encaja=True`: se conserva la proporción del escudo (Dinamic no los estiraba)."""
    return {name: to_game_bmp(image_bytes, size, flatten=(0, 0, 0), flat=True, encaja=True)
            for name, size in ESCUDO_SIZES.items()}


def minifoto_bmp(image_bytes: bytes) -> bytes:
    """Foto de jugador (minifoto 32×32). SIN dither (13-sep-2026).

    Llevaba dither porque es una foto de tono continuo y la paleta fija (halftone) tiene pocos
    tonos de piel: sin él salían manchas verdes/rosas. Pero eso fue ANTES de `face=True`, que
    excluye de la paleta los verdes y azules vívidos que una cara no usa nunca — y con la
    paleta ya acotada, el dither solo aporta ruido: a 32×32 el error se reparte entre píxeles
    que son toda la mejilla, así que la cara sale sembrada de puntos rosas y naranjas (foro,
    13-sep-2026: «aparecen pixeles en los rostros»). Comparado con las minifotos
    originales de PCF7: las de Dinamic son planas, 31 colores frente a los 40 del dither.
    Es lo que v5/6 ya hacía en su minifoto (`photo_set`: la grande con dither, la pequeña sin)."""
    return to_game_bmp(image_bytes, MINIFOTO_SIZE, dither=False, cover=True, face=True)


BIGFOTO_SIZE = (124, 182)


def bigfoto_gif(image_bytes: bytes, fondo: str = "blanco") -> bytes:
    """Foto de FICHA de PCF7: GIF89a de 124×182 con paleta PROPIA.

    Aquí NO manda la paleta fija del juego. Las 893 fotos de ficha originales están en
    `DBDAT/BIGFOTO/EQ98NNNN.PKF` como GIF89a, cada una con su propia tabla de ~161 colores
    —lo comprobamos leyéndolas—, así que se puede cuantizar a medida de cada foto. De ahí
    que estas salgan con calidad fotográfica y sin un solo puntito: el moteado de la
    minifoto viene de tener que encajar cualquier cara en 256 colores fijos, y este formato
    no tiene esa atadura.

    Si la imagen viene recortada sobre transparente (los retratos recortados) se le pone antes
    el fondo, igual que en v5/6."""
    from .photo_bg import con_fondo, tiene_alfa
    src = Image.open(BytesIO(image_bytes))
    if tiene_alfa(src):
        img = con_fondo(src, BIGFOTO_SIZE, fondo)
    else:
        from .image import encuadre_ficha
        img = encuadre_ficha(src, BIGFOTO_SIZE)
    # FASTOCTREE: 0,4 ms por foto frente a 11-24 ms de MEDIANCUT (medido 2026-09-06; a 124×182
    # no se distingue). Con MEDIANCUT, las 2.848 fotos de un mod de PCF7 eran 68 s de los 81 s
    # que tardaba en armarse el ZIP de prueba. (`dither` solo actúa con `palette=`.)
    q = img.quantize(colors=256, method=Image.FASTOCTREE)
    out = BytesIO()
    q.save(out, "GIF", version="GIF89a", optimize=True)
    return out.getvalue()


def bandera_bmp(image_bytes: bytes) -> bytes:
    """Bandera de país (30×20), paleta de banderas. Plana (sin puntitos)."""
    return to_game_bmp(image_bytes, BANDERA_SIZE, palette="banderas", flat=True)


def miniband_bmp(image_bytes: bytes) -> bytes:
    """MINIBANDERA (14×10): la que el juego pinta en las clasificaciones.

    Va aparte de la grande y hay que sacar LAS DOS: si solo se cambia `BANDERAS`, la bandera
    nueva se ve en la ficha del país y la vieja sigue saliendo en las tablas. En v5/6 ya se
    hacía así; en FDI faltaba."""
    return to_game_bmp(image_bytes, MINIBAND_SIZE, palette="banderas", flat=True)


# --- lectura de los escudos EMPAQUETADOS (MINIESC.pkf, EQ98NNNN.BMP) ------------
import re as _re
import struct as _struct
from functools import lru_cache as _lru

_ESC_RE = _re.compile(r"EQ98(\d{4})\.BMP", _re.IGNORECASE)
_FOTO_RE = _re.compile(r"J98(\d{5})\.BMP", _re.IGNORECASE)
_BAND_RE = _re.compile(r"BA96(\d{4})\.BMP", _re.IGNORECASE)
_RX = {"esc": _ESC_RE, "foto": _FOTO_RE, "camiseta": _ESC_RE, "bandera": _BAND_RE}
_PAL = {"esc": "main", "foto": "main", "camiseta": "main", "bandera": "banderas"}


@_lru(maxsize=8)
def _pkf_index(path_str: str, kind: str = "esc") -> dict:
    """{id → (offset, size)} de un PKF de PCF7 (naming según `kind`)."""
    from ..formats.imagenes_pkf import _ENTRY_LEN, _INDEX_START, _KEY
    rx = _RX.get(kind, _ESC_RE)
    data = Path(path_str).read_bytes()
    index: dict[int, tuple[int, int]] = {}
    pos, seen = _INDEX_START, set()
    while 0 <= pos < len(data) and pos not in seen:
        seen.add(pos)
        tag = data[pos]
        if tag == 0x02:
            entry = data[pos:pos + _ENTRY_LEN]
            if len(entry) < _ENTRY_LEN:
                break
            name = bytes(b ^ k for b, k in zip(entry[1:21], _KEY)).split(b"\x00")[0]
            off, size = _struct.unpack_from("<II", entry, 26)
            m = rx.match(name.decode("latin-1", "replace"))
            if m and 0 <= off < len(data) and 0 < size <= len(data) - off:
                index[int(m.group(1))] = (off, size)
            pos += _ENTRY_LEN
        elif tag == 0x04:
            pos = _struct.unpack_from("<I", data, pos + 1)[0]
        else:
            break
    return index


def _packed_bmp(pkf_path, ident: int, kind: str) -> bytes | None:
    from ..formats.imagenes_pkf import dm_to_bmp
    idx = _pkf_index(str(pkf_path), kind)
    ent = idx.get(ident)
    if not ent:
        return None
    data = Path(pkf_path).read_bytes()
    off, size = ent
    try:
        return dm_to_bmp(data[off:off + size], _palette(_PAL.get(kind, "main")))
    except Exception:  # noqa: BLE001
        return None


def packed_escudo_bmp(pkf_path, tid: int) -> bytes | None:
    """Escudo original del juego (BMP) desde el PKF empaquetado, o None."""
    return _packed_bmp(pkf_path, tid, "esc")


def packed_minifoto_bmp(pkf_path, pointer: int) -> bytes | None:
    """Foto de jugador (minifoto) original desde `Minifoto.pkf`, o None."""
    return _packed_bmp(pkf_path, pointer, "foto")


def packed_camiseta_bmp(pkf_path, tid: int) -> bytes | None:
    """Camiseta original desde `CAMISAS.pkf` (naming EQ98NNNN por equipo), o None."""
    return _packed_bmp(pkf_path, tid, "camiseta")


def packed_bandera_bmp(pkf_path, pais: int) -> bytes | None:
    """Bandera original desde `BANDERAS.PKF` (naming BA96NNNN por país), o None."""
    return _packed_bmp(pkf_path, pais, "bandera")


def camiseta_bmp(image_bytes: bytes) -> bytes:
    """Camiseta (73×38) como BMP del juego (paleta main)."""
    return to_game_bmp(image_bytes, (73, 38))


def estadio_bmp(image_bytes: bytes) -> bytes:
    """Foto de estadio (320×240): paleta óptima propia (no la fija)."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB").resize(ESTADIO_SIZE, Image.LANCZOS)
    q = img.quantize(colors=256, dither=Image.FLOYDSTEINBERG)
    out = BytesIO()
    q.save(out, format="BMP")
    return out.getvalue()
