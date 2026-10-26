"""`TEXTOS.PKF` de v5/6 — los POZOS DE NOMBRES por país.

Pese al nombre del fichero no son textos de interfaz: son las listas de nombres de pila y
de apellidos con las que el juego bautiza a los jugadores que se inventa (cantera y
regenerados). Hay una pareja por país —`NOMBRES.<país>` y `APELLIDO.<país>`— y el número
es nuestro mismo código de país: 1 Albania, 10 Brasil, 22 España, 30 Inglaterra. En el
juego original son **108 países**, y España trae 105 nombres y 522 apellidos.

Es el equivalente al `NOMBRES.N` de PCF7, que ya teníamos documentado.

Dos avisos que cuestan una tarde si no se saben:

  · El índice es el del contenedor de imágenes (`imagenes_pkf`), pero **su lector no vale
    aquí**: `imagenes_pkf.parse` filtra los nombres con un patrón de imagen (`EQ96NNNN.BMP`)
    y estas entradas se llaman `APELLIDO.1`, así que devuelve CERO y parece un fichero
    vacío. Hay que recorrer el índice a mano.
  · Cada entrada es un bloque `DMLT`: magia, un u32 propio del bloque, el número de textos
    y luego cada texto con su longitud u16. El texto va cifrado con **XOR 0x61**, como todo
    el formato.

Formato documentado también por PCx-Utils y
verificado leyendo el fichero real.
"""
from __future__ import annotations

import struct

from .imagenes_pkf import _ENTRY_LEN, _entry_name, _index_walk, patch_container

MAGIC = b"DMLT"
XOR = 0x61


def _descifra(b: bytes) -> str:
    return bytes(x ^ XOR for x in b).decode("latin-1")


def _cifra(s: str) -> bytes:
    return bytes(x ^ XOR for x in s.encode("latin-1", "replace"))


def entries(data: bytes) -> dict[str, tuple[int, int]]:
    """`{nombre de entrada: (offset, tamaño)}` recorriendo el índice a mano."""
    out: dict[str, tuple[int, int]] = {}
    for pos, tag in _index_walk(data):
        if tag != 0x02:
            continue
        nombre = _entry_name(data, pos)
        off, size = struct.unpack_from("<II", data[pos:pos + _ENTRY_LEN], 26)
        if nombre and 0 <= off < len(data) and 0 < size <= len(data) - off:
            out[nombre.upper()] = (off, size)
    return out


def read_list(blob: bytes) -> tuple[int, list[str]]:
    """`(id del bloque, [textos])` de un bloque DMLT. `(0, [])` si no lo es."""
    if blob[:4] != MAGIC or len(blob) < 12:
        return 0, []
    ident, n = struct.unpack_from("<II", blob, 4)
    o, out = 12, []
    for _ in range(n):
        if o + 2 > len(blob):
            break
        ln = struct.unpack_from("<H", blob, o)[0]
        o += 2
        out.append(_descifra(blob[o:o + ln]))
        o += ln
    return ident, out


def write_list(ident: int, textos: list[str]) -> bytes:
    """Bloque DMLT con esos textos.

    El u32 que va tras la magia NO es un identificador opaco (así lo dábamos por
    bueno y así lo conservábamos): es **la suma de las longitudes más el número de
    textos**, o sea lo que ocupan los nombres si cada uno acabase en un cero — el
    sitio que el juego reserva antes de leer la lista. Verificado en las 435 listas
    de las dos ediciones que traen el fichero, sin excepción.

    Por eso se RECALCULA. Conservar el viejo al añadir nombres le decía al juego
    que reservase menos memoria de la que le íbamos a dar. `ident` se acepta por
    compatibilidad de la firma, pero se ignora.
    """
    cifrados = [_cifra(t) for t in textos]
    cuenta = sum(len(b) for b in cifrados) + len(cifrados)   # + el cero de cada uno
    out = bytearray(MAGIC)
    out += struct.pack("<II", cuenta, len(cifrados))
    for b in cifrados:
        out += struct.pack("<H", len(b)) + b
    return bytes(out)


def name_pools(data: bytes) -> dict[int, dict]:
    """`{código de país: {"nombres": [...], "apellidos": [...]}}`."""
    ent = entries(data)
    out: dict[int, dict] = {}
    for nombre, (off, size) in ent.items():
        familia, _, num = nombre.partition(".")
        if familia not in ("NOMBRES", "APELLIDO") or not num.isdigit():
            continue
        clave = "nombres" if familia == "NOMBRES" else "apellidos"
        _ident, textos = read_list(data[off:off + size])
        out.setdefault(int(num), {}).setdefault(clave, textos)
    return out


# Además de los pozos de nombres, el fichero trae los NOMBRES DE LOS PAÍSES tal como los
# escribe el juego, uno por idioma: `PAISES.22` español, `PAISES.24` francés, `PAISES.30`
# inglés y `PAISES.36` italiano (el número es el código de país del idioma, el mismo que el
# byte de idioma del bloque de equipo). Son 128 textos, uno por código de país, en el orden
# de la tabla del juego: 0 «XXX», 1 Albania, 2 Alemania… 22 España.
LANG_NAMES = {22: "Español", 24: "Francés", 30: "Inglés", 36: "Italiano"}


def country_names(data: bytes) -> dict[int, list[str]]:
    """`{código de idioma: [nombre por código de país]}`."""
    out: dict[int, list[str]] = {}
    for nombre, (off, size) in entries(data).items():
        familia, _, num = nombre.partition(".")
        if familia != "PAISES" or not num.isdigit():
            continue
        out[int(num)] = read_list(data[off:off + size])[1]
    return out


def patch_country_names(data: bytes, langs: dict) -> bytes:
    """Contenedor con los nombres de país cambiados. `langs` = `{idioma: [nombres]}`;
    lo que no venga se deja como estaba. Se conserva el nº de textos de cada lista: el
    juego indexa por posición, así que añadir o quitar la descuadraría entera."""
    ent = entries(data)
    entradas: dict[str, bytes] = {}
    for idioma, textos in (langs or {}).items():
        nombre = f"PAISES.{int(idioma)}"
        sitio = ent.get(nombre)
        if not sitio or textos is None:
            continue
        original = data[sitio[0]:sitio[0] + sitio[1]]
        ident, viejos = read_list(original)
        nuevos = [str(t) if t is not None else v for t, v in zip(textos, viejos)]
        nuevos += viejos[len(nuevos):]                  # nunca se acorta la lista
        nuevo = write_list(ident, nuevos)
        if nuevo != original:
            entradas[nombre] = nuevo
    return patch_container(data, entradas) if entradas else data


def patch_pools(data: bytes, pools: dict) -> bytes:
    """Contenedor con los pozos cambiados. `pools` = `{país: {"nombres": [...],
    "apellidos": [...]}}`; lo que no venga se deja como estaba.

    Los bloques cambian de tamaño, así que se reempaqueta el contenedor entero
    (`patch_container` los sustituye y recoloca sin tocar los demás)."""
    ent = entries(data)
    entradas: dict[str, bytes] = {}
    for pais, campos in (pools or {}).items():
        for clave, familia in (("nombres", "NOMBRES"), ("apellidos", "APELLIDO")):
            textos = (campos or {}).get(clave)
            if textos is None:
                continue
            nombre = f"{familia}.{int(pais)}"
            sitio = ent.get(nombre)
            original = data[sitio[0]:sitio[0] + sitio[1]] if sitio else b""
            ident = read_list(original)[0] if sitio else 0
            nuevo = write_list(ident, [str(t) for t in textos if str(t).strip()])
            # lo que no cambia NO se toca: `patch_container` ANEXA siempre, así que
            # reescribir un bloque idéntico engordaba el fichero sin motivo y rompía el
            # round-trip byte-perfecto.
            if nuevo != original:
                entradas[nombre] = nuevo
    return patch_container(data, entradas) if entradas else data
