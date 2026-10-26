"""PCF 3.0 — contenedor de GRÁFICOS `.DGF` (caras de jugador).

`EQUIP/LIG{1|2}EQ{NN}.DGF` = gráficos de un equipo. Firma `Copyright (c)1993,94 Dinamic Multimedia`
+ una concatenación de imágenes en el MISMO formato que los `.DFG` de PCF 4 (paleta EN
fichero): `[00 10][paleta 16×RGB][01 W 00 H 00 04 00 00][4 bitplanes][FF]`. Se decodifican con el
códec de PCF4 (`codec/pcf4_image.decode_bitplane_palfile`).

Por equipo hay, en orden de plantilla: un **mini retrato 24×24** y (para los jugadores con foto) una
**cara grande 124×182** (mismas dims que el BIGFOTO de PCF4). 
"""
from __future__ import annotations

from io import BytesIO

from ..codec import pcf4_image as IMG

_MARK = b"\x00\x10"
_SIG_SKIP = 36        # saltar la firma "Copyright…Dinamic Multimedia"


def images(data: bytes) -> list[dict]:
    """Lista las imágenes del contenedor: [{off, w, h, size, kind}] (kind = 'mini' | 'big').
    Algunos `.DGF` llevan firma `Copyright…Dinamic` antes del primer marcador (empieza en ~38),
    otros arrancan directamente con el marcador `00 10` en el offset 0."""
    out: list[dict] = []
    pos = 0 if data[:2] == _MARK else data.find(_MARK, _SIG_SKIP)
    while pos >= 0 and pos + 58 < len(data) and data[pos:pos + 2] == _MARK:
        hdr = data[pos + 50:pos + 58]
        if hdr[0] != 0x01 or hdr[5] != 0x04:
            break
        w = hdr[1] | (hdr[2] << 8)
        h = hdr[3] | (hdr[4] << 8)
        if not (0 < w <= 256 and 0 < h <= 256):
            break
        bpr = (w + 7) // 8
        size = 2 + 48 + 8 + h * 4 * bpr + 1        # marcador + paleta + cabecera + planos + FF
        if pos + size > len(data):
            break
        out.append({"off": pos, "w": w, "h": h, "size": size,
                    "kind": "big" if h > 60 else "mini"})
        pos += size
    return out


def faces(data: bytes) -> list[dict]:
    """Caras grandes (124×182) en orden de plantilla."""
    return [im for im in images(data) if im["kind"] == "big"]


def minis(data: bytes) -> list[dict]:
    """Mini retratos (24×24) en orden de plantilla."""
    return [im for im in images(data) if im["kind"] == "mini"]


def decode_png(data: bytes, im: dict, scale: int = 1,
               key: "tuple[int, int, int] | str | None" = None) -> bytes:
    """Decodifica una imagen del contenedor a PNG. Si `key` es un color RGB (o `"auto"` = el color de
    la esquina superior-izquierda, robusto a paletas donde el "blanco" no es 255,255,255 —p.ej. 2ª usa
    251,251,251—), el fondo de ese color CONECTADO AL BORDE se hace transparente (relleno desde los
    bordes → no agujerea los colores internos del dibujo)."""
    from collections import deque

    from PIL import Image
    rgb, w, h = IMG.decode_bitplane_palfile(data[im["off"]:im["off"] + im["size"]])
    img = Image.frombytes("RGB", (w, h), rgb)
    if key == "auto":
        key = img.getpixel((0, 0))       # color de fondo = esquina (el escudo lleva marco de fondo)
    if key is not None:
        img = img.convert("RGBA")
        px = img.load()
        seen = bytearray(w * h)
        dq: deque = deque()
        for x in range(w):
            dq.append((x, 0))
            dq.append((x, h - 1))
        for y in range(h):
            dq.append((0, y))
            dq.append((w - 1, y))
        while dq:
            x, y = dq.popleft()
            if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x]:
                continue
            seen[y * w + x] = 1
            r, g, b, a = px[x, y]
            if (r, g, b) != key:
                continue                            # frontera del dibujo → no seguir
            px[x, y] = (r, g, b, 0)                  # fondo → transparente
            dq.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    if scale > 1:
        img = img.resize((w * scale, h * scale), Image.NEAREST)
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def division_teams(data: bytes) -> list[dict]:
    """Del `LIG9495N.DGF` de división: por equipo (en orden) sus 4 gráficos.
    Cada bloque de equipo = [escudo 48×64][escudo GRANDE ~120×170][kit 71×37][equipación 200×140].
    Devuelve [{esc, escbig, kit_s, kit_b}] (imágenes o None)."""
    ims = images(data)
    starts = [i for i, im in enumerate(ims) if (im["w"], im["h"]) == (48, 64)]
    out: list[dict] = []
    for k, si in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(ims)
        t = {"esc": None, "escbig": None, "kit_s": None, "kit_b": None}
        for im in ims[si:end]:
            w, h = im["w"], im["h"]
            if (w, h) == (48, 64):
                t["esc"] = im
            elif (w, h) == (200, 140):
                t["kit_b"] = im
            elif (w, h) in ((71, 37), (70, 37)):
                t["kit_s"] = im
            elif h > 100:
                t["escbig"] = im
        out.append(t)
    return out


def _es_escudo_grande(im: dict) -> bool:
    """Escudo grande (~120×170). Se distingue del estadio (200×140), que también es alto."""
    return im["h"] > 100 and (im["w"], im["h"]) != (200, 140) and im["w"] < 160


def team_graphics_at(data: bytes, esc_off: int) -> dict | None:
    """Los 4 gráficos del equipo cuyo escudo 48×64 está en `esc_off` (ANCLADO por el puntero del
    DBC, no por orden). Devuelve {esc, escbig, kit_s, kit_b} (imágenes o None).

    OJO — LAS DOS DIVISIONES NO GUARDAN LOS GRÁFICOS EN EL MISMO ORDEN (2026-08-30):

        1ª:  [escudo 48×64] [escudo grande] [equipación 71×37] [estadio 200×140]
        2ª:  [escudo grande] [escudo 48×64] [equipación 71×37]          (sin estadio)

    Tomar el bloque «del escudo pequeño al siguiente escudo pequeño» vale en 1ª, pero en 2ª deja
    el escudo grande de CADA equipo dentro del bloque del ANTERIOR: en la ficha del Rayo salía el
    escudo del Lleida, y así todos corridos uno. Por eso, si justo ANTES del escudo pequeño hay un
    escudo grande, ese es el de este equipo.
    """
    ims = images(data)
    idx = next((k for k, im in enumerate(ims)
                if im["off"] == esc_off and (im["w"], im["h"]) == (48, 64)), None)
    if idx is None:
        return None
    end = len(ims)
    for k in range(idx + 1, len(ims)):
        if (ims[k]["w"], ims[k]["h"]) == (48, 64):
            end = k
            break
    t = {"esc": None, "escbig": None, "kit_s": None, "kit_b": None}
    for im in ims[idx:end]:
        w, h = im["w"], im["h"]
        if (w, h) == (48, 64):
            t["esc"] = im
        elif (w, h) == (200, 140):
            t["kit_b"] = im
        elif (w, h) in ((71, 37), (70, 37)):
            t["kit_s"] = im
        elif _es_escudo_grande(im):
            t["escbig"] = im
    if idx and _es_escudo_grande(ims[idx - 1]):      # orden de 2ª: el grande va DELANTE
        t["escbig"] = ims[idx - 1]
    return t


def image_at(data: bytes, off: int) -> dict | None:
    """La imagen cuyo offset es exactamente `off` (los punteros de foto del DBC apuntan aquí)."""
    for im in images(data):
        if im["off"] == off:
            return im
    return None


def png_at_offset(data: bytes, off: int) -> bytes | None:
    im = image_at(data, off)
    return decode_png(data, im) if im else None


def slots(data: bytes) -> list[dict]:
    """Agrupa las imágenes por JUGADOR: cada jugador = un mini 24×24 y, si tiene foto, la cara
    grande 124×182 que va justo después. Devuelve [{mini, big}] en orden de plantilla (big=None si
    ese jugador no tiene cara grande). Así el jugador i de la BBDD → slot i."""
    ims = images(data)
    out: list[dict] = []
    i = 0
    while i < len(ims):
        if ims[i]["kind"] == "mini":
            big = ims[i + 1] if i + 1 < len(ims) and ims[i + 1]["kind"] == "big" else None
            out.append({"mini": ims[i], "big": big})
            i += 2 if big else 1
        else:
            # cara grande suelta sin mini previo (raro): slot propio
            out.append({"mini": None, "big": ims[i]})
            i += 1
    return out


def _is_blank(data: bytes, im: dict) -> bool:
    """True si la imagen es un placeholder (>80% de un solo color = sin foto)."""
    from collections import Counter
    rgb, w, h = IMG.decode_bitplane_palfile(data[im["off"]:im["off"] + im["size"]])
    px = [rgb[i:i + 3] for i in range(0, len(rgb), 3)]
    return Counter(px).most_common(1)[0][1] > 0.80 * len(px)


def coach_index(data: bytes) -> int:
    """Índice de imagen del ENTRENADOR en un roster de 1ª. El técnico es un mini 24×24 situado
    hacia el final del contenedor: se parte de `nº imágenes − 7` y se retrocede hasta el primer
    mini con cara real (saltando huecos/placeholders de jugadores sin foto). VERIFICADO a ojo
    (Cruyff, Camacho…). En 2ª NO hay foto de entrenador. Devuelve -1 si no se encuentra."""
    ims = images(data)
    i = len(ims) - 7
    while i >= 0:
        im = ims[i]
        if (im["w"], im["h"]) == (24, 24) and not _is_blank(data, im):
            return i
        i -= 1
    return -1


def coach_png(data: bytes) -> bytes | None:
    """PNG del retrato del entrenador (mini 24×24), o None si no hay."""
    ims = images(data)
    ci = coach_index(data)
    if ci < 0:
        return None
    return decode_png(data, ims[ci])


def player_png(data: bytes, idx: int, big: bool = True) -> bytes | None:
    """PNG del jugador nº `idx` (orden de plantilla): la cara grande (o el mini si no hay/ si
    `big=False`). None si ese jugador no tiene imagen."""
    sl = slots(data)
    if not (0 <= idx < len(sl)):
        return None
    im = sl[idx]["big"] if (big and sl[idx]["big"]) else sl[idx]["mini"]
    return decode_png(data, im) if im else None


def face_png(data: bytes, idx: int) -> bytes | None:
    """PNG de la cara grande nº `idx` (entre las que tienen foto grande)."""
    fs = faces(data)
    if not (0 <= idx < len(fs)):
        return None
    return decode_png(data, fs[idx])


# -- mover un equipo de división (RE 2026-08-29) -------------------------------------------------
# El contenedor NO tiene índice ni contador: es una ristra de imágenes autodescriptivas que se
# recorre de principio a fin (`images()`), y en los dos `.DGF` de división no sobra ni un byte tras
# la última. Por eso ANEXAR al final es seguro: la imagen nueva se alcanza siguiendo la ristra y no
# se desplaza nada de lo que ya había (ningún puntero existente cambia de sitio).

def group_range(data: bytes, esc_off: int) -> "tuple[int, int] | None":
    """(inicio, fin) de los bytes del grupo de gráficos cuyo escudo 48×64 está en `esc_off`.
    El grupo va desde ese escudo hasta el siguiente 48×64 (o hasta el final)."""
    ims = images(data)
    idx = next((k for k, im in enumerate(ims)
                if im["off"] == esc_off and (im["w"], im["h"]) == (48, 64)), None)
    if idx is None:
        return None
    for k in range(idx + 1, len(ims)):
        if (ims[k]["w"], ims[k]["h"]) == (48, 64):
            return ims[idx]["off"], ims[k]["off"]
    ultima = ims[-1]
    return ims[idx]["off"], ultima["off"] + ultima["size"]


def group_bytes(data: bytes, esc_off: int) -> "bytes | None":
    r = group_range(data, esc_off)
    return data[r[0]:r[1]] if r else None


def append_group(data: bytes, grupo: bytes) -> "tuple[bytes, int]":
    """Anexa un grupo de gráficos y devuelve (contenedor nuevo, offset del escudo nuevo).
    Se pega justo detrás de la última imagen —no al final del fichero— para que el recorrido de
    `images()` llegue hasta él aunque algún día aparezca relleno al final."""
    ims = images(data)
    fin = ims[-1]["off"] + ims[-1]["size"] if ims else len(data)
    return data[:fin] + grupo + data[fin:], fin


# -- sustituir una imagen (2026-08-30) ---------------------------------------------------------
# Cada imagen del `.DGF` lleva SU PROPIA paleta de 16 colores dentro, y las medidas van en su
# cabecera. Como se reescribe con las MISMAS medidas, ocupa exactamente los mismos bytes: el
# contenedor no cambia de tamaño y ningún puntero —ni el del escudo del equipo, ni los de las
# fotos de los jugadores— se mueve de sitio.
#
# La paleta se REHACE para la imagen nueva (adaptativa de 16 colores) en vez de reaprovechar la
# vieja: como cada imagen guarda la suya, es seguro, y una foto de estadio metida a la fuerza en
# la paleta de otra sale con colores que no son.

def replace_image(data: bytes, im: dict, png: bytes) -> bytes:
    """Contenedor con la imagen `im` sustituida por `png` (reescalado a sus medidas)."""
    from ..codec import pcf4_image as IMG
    nuevo = IMG.encode_palfile_exact(png, im["w"], im["h"])
    if len(nuevo) != im["size"]:
        raise ValueError(f"la imagen nueva ocuparía {len(nuevo)} bytes y el hueco es de {im['size']}")
    return data[:im["off"]] + nuevo + data[im["off"] + im["size"]:]
