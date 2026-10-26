"""Lector de contenedores de imágenes PKF (NANOESC/MINIESC/RIDIESC/MINIFOTO).

Formato (ingeniería inversa 2026-07-01):

- Cabecera de 232 bytes. A partir de ahí, registros con byte de tipo:
  * ``02`` — entrada de fichero (38 bytes): nombre cifrado (20B) + 5B pad +
    offset u32 + tamaño u32 + u32 (=1).
  * ``04`` — salto: u32 con la posición donde sigue el índice (el índice va
    en secciones intercaladas con los datos de imagen).
  * ``05`` — fin del contenedor.
- Nombre cifrado con **XOR posicional**: keystream k0=0xDF y diferencias
  impares decrecientes (0x1F, 0x1D, …). Descifrado: ``EQ960004.BMP`` /
  ``J9600001.BMP`` — el número es el puntero canónico (equipo 4 cifras,
  jugador 5 cifras). Los contenedores usan prefijo 96 en todas las versiones.
- Cada imagen es un BMP de 8bpp con magia ``DM`` (Dinamic) y **sin paleta**:
  cabecera BITMAPFILEHEADER+INFO estándar (el offset a píxeles asume paleta
  de 1024B presente) seguida directamente de los píxeles. La paleta la pone
  el juego (la fija de refdata).
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass

_INDEX_START = 232
_ENTRY_LEN = 38
_NAME_RE = re.compile(r"^[A-Z]+96(\d{4,5})\.")


def _keystream(n: int = 20) -> bytes:
    ks, k, d = [], 0xDF, 0x1F
    for _ in range(n):
        ks.append(k)
        k = (k - d) & 0xFF
        d -= 2
    return bytes(ks)


_KEY = _keystream()


@dataclass
class ImageContainer:
    """Índice de un contenedor: puntero -> blob DM (BMP sin paleta)."""
    data: bytes
    index: dict[int, tuple[int, int]]  # puntero -> (offset, tamaño)

    def blob(self, pointer: int) -> bytes | None:
        loc = self.index.get(pointer)
        if not loc:
            return None
        off, size = loc
        return self.data[off:off + size]

    @property
    def pointers(self) -> set[int]:
        return set(self.index)


def parse(data: bytes) -> ImageContainer:
    """Recorre las secciones del índice y descifra los nombres."""
    index: dict[int, tuple[int, int]] = {}
    pos, seen = _INDEX_START, set()
    while 0 <= pos < len(data) and pos not in seen:
        seen.add(pos)
        tag = data[pos]
        if tag == 0x02:
            entry = data[pos:pos + _ENTRY_LEN]
            if len(entry) < _ENTRY_LEN:
                break
            name_bytes = bytes(b ^ k for b, k in zip(entry[1:21], _KEY))
            name = name_bytes.split(b"\x00")[0].decode("latin-1", "replace")
            off, size = struct.unpack_from("<II", entry, 26)
            m = _NAME_RE.match(name)
            if m and 0 <= off < len(data) and 0 < size <= len(data) - off:
                index[int(m.group(1))] = (off, size)
            pos += _ENTRY_LEN
        elif tag == 0x04:
            pos = struct.unpack_from("<I", data, pos + 1)[0]
        else:
            break
    return ImageContainer(data=data, index=index)


def dm_to_bmp(blob: bytes, palette: list[int]) -> bytes:
    """Blob de contenedor (BMP 8bpp SIN paleta) -> BMP estándar con la paleta dada.

    Los contenedores mezclan dos variantes de cabecera, ambas sin paleta:
    - magia ``DM`` + BITMAPINFOHEADER (40B): píxeles a partir del byte 54.
    - magia ``BM`` + BITMAPCOREHEADER (12B, dimensiones u16): píxeles en el 26.
    Muchos blobs vienen además con los últimos bytes de píxel recortados (el
    juego lo tolera); rellenamos con 0 (negro = transparente en el juego).
    """
    if len(blob) < 26 or blob[:2] not in (b"DM", b"BM"):
        raise ValueError("blob de imagen no reconocido")
    bisize = struct.unpack_from("<I", blob, 14)[0]
    if bisize == 40:
        width = struct.unpack_from("<i", blob, 18)[0]
        height = struct.unpack_from("<i", blob, 22)[0]
        pixels = blob[54:]
    elif bisize == 12:
        width, height = struct.unpack_from("<HH", blob, 18)
        pixels = blob[26:]
    else:
        raise ValueError(f"cabecera BMP no reconocida (biSize={bisize})")
    if not (0 < width <= 1024 and 0 < abs(height) <= 1024):
        raise ValueError(f"dimensiones no válidas: {width}x{height}")
    stride = (width + 3) & ~3
    need = stride * abs(height)
    if len(pixels) < need:
        pixels = pixels + b"\x00" * (need - len(pixels))
    header = bytearray(54)
    header[0:2] = b"BM"
    struct.pack_into("<IHHI", header, 2, 54 + 1024 + need, 0, 0, 54 + 1024)
    struct.pack_into("<IiiHH", header, 14, 40, width, height, 1, 8)
    pal = bytearray()
    for i in range(256):
        pal += bytes((palette[i * 3 + 2], palette[i * 3 + 1], palette[i * 3], 0))
    return bytes(header) + bytes(pal) + pixels[:need]


def first_member_prefix(data: bytes) -> str | None:
    """Prefijo de temporada ("96"/"97") del primer miembro del índice, leído
    del nombre cifrado (EQ97xxxx.DBC, EQ96xxxx.BMP...). None si no se puede."""
    import re as _re
    import struct as _struct
    try:
        pos = _INDEX_START
        seen = set()
        while 0 <= pos < len(data) and pos not in seen:
            seen.add(pos)
            tag = data[pos]
            if tag == 4:
                pos = _struct.unpack_from("<I", data, pos + 1)[0]
                continue
            if tag != 2:
                return None
            name = bytes(b ^ k for b, k in zip(data[pos + 1:pos + 21], _KEY))
            name = name.split(b"\x00")[0].decode("latin-1", "replace")
            m = _re.match(r"(?:EQ|J)(\d{2})", name.upper())
            return m.group(1) if m else None
    except Exception:  # noqa: BLE001
        return None
    return None


# ---------------------------------------------------------------------------
# AÑADIR / SUSTITUIR imágenes en un contenedor (2026-08-16)
#
# El índice va en SECCIONES encadenadas: cada una es una ristra de entradas 0x02 y
# termina o bien en un salto 0x04 (u32 con la posición de la siguiente) o bien en 0x05.
# Eso da dos operaciones sin reescribir el fichero:
#
#   SUSTITUIR una imagen → se APENDA el blob nuevo al final y se parchea el offset y el
#     tamaño de su entrada. Los demás offsets, que son absolutos, no se mueven.
#   AÑADIR una imagen que no existía → el terminador 0x05 se convierte en un salto a una
#     sección NUEVA pegada al final, con las entradas nuevas y su propio 0x05. Cabe justo:
#     tras el 0x05 el fichero deja 4 bytes a cero y el salto ocupa 5.
#
# Verificado sobre `estadio.pkf` de PCF7: de 20 a 22 entradas, las 20 originales intactas,
# las nuevas se decodifican y del fichero original solo cambian 5 bytes.
# PENDIENTE VALIDAR EN JUEGO: que el juego siga el salto igual que nuestro lector.
# ---------------------------------------------------------------------------
def _index_walk(data: bytes):
    """[(posición, tag)] de los registros del índice, en orden."""
    pos, seen, out = _INDEX_START, set(), []
    while 0 <= pos < len(data) and pos not in seen:
        seen.add(pos)
        tag = data[pos]
        out.append((pos, tag))
        if tag == 0x02:
            pos += _ENTRY_LEN
        elif tag == 0x04:
            pos = struct.unpack_from("<I", data, pos + 1)[0]
        else:
            break
    return out


def _entry_name(data: bytes, pos: int) -> str:
    raw = bytes(b ^ k for b, k in zip(data[pos + 1:pos + 21], _KEY))
    return raw.split(b"\x00")[0].decode("latin-1", "replace")


def entries(data: bytes) -> list[str]:
    """Nombres de las imágenes que el contenedor YA tiene, en el orden del índice."""
    return [_entry_name(data, pos) for pos, tag in _index_walk(data) if tag == 0x02]


def ocultar_entradas(data: bytes, nombres) -> bytes:
    """Devuelve el contenedor con esas entradas INVISIBLES para el juego.

    No se borra nada: el juego busca cada imagen por su nombre («eq980001»), así que basta con
    renombrar la entrada para que no la encuentre y se comporte igual que con un equipo que
    nunca tuvo esa imagen. En la foto de estadio eso significa que dibuja el estadio genérico,
    el que va cambiando de forma según las gradas que construyes — que es justo lo que se pidió
    en el foro (26-ago-2026).

    Se hace así y no poniendo el tamaño a 0 porque un tamaño 0 obliga al juego a leer una
    imagen vacía; con el nombre cambiado ni siquiera llega a buscarla. Y es REVERSIBLE: los
    bytes de la imagen siguen enteros donde estaban.
    """
    objetivo = {n.upper() for n in nombres}
    if not objetivo:
        return data
    d = bytearray(data)
    for pos, tag in _index_walk(bytes(d)):
        if tag != 0x02 or _entry_name(bytes(d), pos).upper() not in objetivo:
            continue
        # el nombre va cifrado con `_KEY`; se le cambia la primera letra por «~», que no
        # aparece en ningún nombre real del juego y deja el resto legible para diagnosticar
        d[pos + 1] = ord("~") ^ _KEY[0]
    return bytes(d)


def patch_container(data: bytes, entradas: dict, permitir_nuevas: bool = True) -> bytes:
    """Devuelve el contenedor con esas imágenes puestas. `entradas` = {nombre: blob DM}.

    Las que ya existen se sustituyen; las que no, se añaden. El tamaño del fichero crece,
    pero ni una sola imagen previa se toca.

    Con `permitir_nuevas=False` solo se SUSTITUYE: las que no existan se ignoran y el índice
    se queda exactamente como estaba. Es el modo prudente, para los contenedores en los que
    todavía no está confirmado que el juego siga el salto de sección (ver la nota de arriba):
    sustituir solo repunta cuatro bytes de una entrada que el juego ya recorría, mientras que
    añadir le pide recorrer un índice con una forma que nunca ha tenido en el fichero real."""
    d = bytearray(data)
    pos_por_nombre = {}
    fin = None
    for pos, tag in _index_walk(bytes(d)):
        if tag == 0x02:
            pos_por_nombre[_entry_name(bytes(d), pos).upper()] = pos
        elif tag == 0x05:
            fin = pos
    nuevas = {}
    for nombre, blob in entradas.items():
        p = pos_por_nombre.get(nombre.upper())
        if p is None:
            nuevas[nombre] = blob
            continue
        off = len(d)
        d += blob
        struct.pack_into("<II", d, p + 26, off, len(blob))     # offset y tamaño
    if not nuevas or not permitir_nuevas:
        return bytes(d)
    if fin is None or bytes(d[fin:fin + 5]) != b"\x05\x00\x00\x00\x00":
        raise ValueError("no hay sitio para añadir entradas en este contenedor")
    seccion = len(d)
    struct.pack_into("<BI", d, fin, 0x04, seccion)             # el fin pasa a ser un salto
    idx, blobs = bytearray(), bytearray()
    base = seccion + len(nuevas) * _ENTRY_LEN + 5              # tras el 0x05 de la sección
    for nombre, blob in nuevas.items():
        nm = nombre.encode("latin-1", "replace").ljust(20, b"\x00")[:20]
        e = bytearray(_ENTRY_LEN)
        e[0] = 0x02
        e[1:21] = bytes(b ^ k for b, k in zip(nm, _KEY))
        struct.pack_into("<III", e, 26, base + len(blobs), len(blob), 1)
        idx += e
        blobs += blob
    idx += b"\x05\x00\x00\x00\x00"
    return bytes(d + idx + blobs)


def _pixeles_de(bmp: bytes) -> tuple[int, int, bytes]:
    """(ancho, alto, píxeles de abajo arriba) de un BMP estándar de 8 bpp."""
    if len(bmp) < 54 or bmp[:2] != b"BM":
        raise ValueError("no es un BMP")
    bisize = struct.unpack_from("<I", bmp, 14)[0]
    if bisize != 40 or struct.unpack_from("<H", bmp, 28)[0] != 8:
        raise ValueError("se esperaba un BMP de 8 bits con cabecera de 40 bytes")
    w, h = struct.unpack_from("<ii", bmp, 18)
    off = struct.unpack_from("<I", bmp, 10)[0]
    px = bmp[off:]
    stride = (w + 3) & ~3
    px = px[:stride * abs(h)].ljust(stride * abs(h), b"\x00")
    if h < 0:      # BMP de arriba abajo: se le da la vuelta, que es como van los del juego
        px = b"".join(px[i * stride:(i + 1) * stride] for i in reversed(range(abs(h))))
    return w, abs(h), px


def member_blob(data: bytes, nombre: str | None = None) -> bytes | None:
    """La imagen que el contenedor guarda con ese nombre (o la PRIMERA, si no se da).

    Sirve de modelo de cabecera para `bmp_to_member`: cada contenedor es homogéneo, así que
    cualquiera de sus miembros dice en qué variante hay que escribir."""
    for pos, tag in _index_walk(data):
        if tag != 0x02:
            continue
        if nombre is None or _entry_name(data, pos).upper() == nombre.upper():
            off, size = struct.unpack_from("<II", data, pos + 26)
            return data[off:off + size]
    return None


def bmp_to_member(bmp: bytes, modelo: bytes | None = None) -> bytes:
    """BMP estándar de 8 bpp -> blob de contenedor, **en la variante de `modelo`**.

    Los contenedores guardan la imagen SIN tabla de paleta (la pone el juego), pero no todos
    con la misma cabecera, y cada fichero es coherente consigo mismo. Medido en `gamedata`:

        5.0 original                          magia ``DM`` + cabecera de 40  (43 de 43)
        5.0 Oro, 6.0 original, 6.0 Oro        magia ``BM`` + cabecera de 12  (todas)

    Escribir la variante que no es deja una imagen que el juego no sabe leer donde antes
    había una buena, así que el modelo es SIEMPRE el miembro al que se sustituye. Sin modelo
    se mantiene el comportamiento histórico (``DM``), que es el de 5.0 original.
    """
    w, h, px = _pixeles_de(bmp)
    if modelo is not None and len(modelo) >= 26 and modelo[:2] in (b"BM", b"DM"):
        core = struct.unpack_from("<I", modelo, 14)[0] == 12
        largo = 26 if core else 54
        w0, h0 = (struct.unpack_from("<HH", modelo, 18) if core
                  else tuple(abs(v) for v in struct.unpack_from("<ii", modelo, 18)))
        if (w0, h0) == (w, h):
            # misma medida: se conserva la cabecera TAL CUAL y solo se cambian los píxeles.
            # Así la ida y vuelta es byte a byte, incluidos los campos que el juego escribió
            # a su manera (el `filesize` de 5.0 original, por ejemplo, ni siquiera cuadra).
            # Y se conserva también la COLA: dos tercios de las imágenes del juego llevan un
            # `00 00` detrás de los píxeles (34 de las 50 de BIGENTR en 6.0, 465 de las 484
            # de NANOESC), y el blob tiene que salir del mismo tamaño que entró.
            return modelo[:largo] + px + modelo[largo + len(px):]
        if core:
            cab = bytearray(26)
            cab[0:2] = b"BM"
            struct.pack_into("<III", cab, 2, 26 + len(px), 0, 26)
            struct.pack_into("<IHHHH", cab, 14, 12, w, h, 1, 8)
            return bytes(cab) + px
        # cabecera de 40 pero de otra medida: se rehace, conservando la MAGIA del modelo
        # (`BM` en Apertura 98 y en el MINIENTR de PCF7; `DM` solo en 5.0 original).
        cab = bytearray(bmp[:54])
        cab[0:2] = modelo[:2]
        return bytes(cab) + px
    cab = bytearray(bmp[:54])
    cab[0:2] = b"DM"
    return bytes(cab) + px


def bmp_to_dm(bmp: bytes) -> bytes:
    """Compatibilidad: la variante ``DM`` suelta. Preferir `bmp_to_member`, que copia la del
    contenedor de destino."""
    return bmp_to_member(bmp)
