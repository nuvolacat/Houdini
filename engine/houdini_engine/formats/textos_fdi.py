"""Bancos de texto de las ediciones FDI (7.0, 2000 y 2001).

Son los mismos tres que en 5.0/6.0 y viven en el mismo sitio conceptual, pero repartidos en
**dos contenedores distintos** según la edición:

* **PCF7** → `DBDAT/textos.pkf`, contenedor PKF, el mismo de v5/6 (341 entradas).
* **PCF2000 y 2001** → `DBDAT/TEXTOS.PAK`, contenedor `PAK_` (219 entradas).

Dentro, los dos guardan bloques **DMLT** idénticos a los de v5/6, así que `read_list` y
`write_list` valen tal cual. Lo que hay dentro:

* `PAISES.<idioma>` — los nombres de los 207 países tal como los escribe el juego. Son
  **cinco idiomas** en 2000/2001 (22 español, 24 francés, 30 inglés, 36 italiano y 2 alemán)
  y cuatro en PCF7. El índice de la lista es el código de país, el mismo que usamos nosotros.
* `NOMBRES.<país>` y `APELLIDO.<país>` — los pozos con los que el juego bautiza a los
  jugadores que se inventa (cantera y regenerados). Unos 107 países por edición.

Que el juego los lee de verdad no es suposición: el `manager.exe` de las TRES ediciones trae
las rutas `dbdat\\textos\\paises.%u`, `nombres.%u` y `apellido.%u`.

**Gotcha del contenedor PAK:** sus nombres de entrada van CIFRADOS y el detector de la clave
exigía que la ruta acabara en una extensión de imagen. Aquí acaban en el código de país
(`PAISES.22`), así que fallaba y devolvía basura; `pak._detect_prefix_char` tiene ahora una
segunda vuelta para eso.
"""
from __future__ import annotations

from ..codec import pak as _PAK
from . import textos_pkf as _TX

# familias y su clave en la API
FAMILIAS = {"NOMBRES": "nombres", "APELLIDO": "apellidos"}
# idiomas que traen los contenedores FDI (el 2, alemán, solo está en 2000/2001)
LANG_NAMES = {2: "Alemán", 22: "Español", 24: "Francés", 30: "Inglés", 36: "Italiano"}


def es_pak(data: bytes) -> bool:
    return data[:4] == _PAK.MAGIC


def entradas(data: bytes) -> dict[str, tuple[int, int]]:
    """`{nombre de entrada: (offset, largo)}`, ya sea PKF o PAK.

    En el PAK la entrada se llama `TEXTOS\\PAISES.22`; se queda solo con el nombre de
    fichero para que las dos familias de contenedor se manejen igual."""
    if not es_pak(data):
        return _TX.entries(data)
    out: dict[str, tuple[int, int]] = {}
    for nombre, init, largo, _hdr in _PAK.index_var(data):
        corto = nombre.replace("/", "\\").split("\\")[-1]
        out[corto.upper()] = (init, largo)
    return out


def _lee(data: bytes, sitio: tuple[int, int]) -> tuple[int, list[str]]:
    return _TX.read_list(data[sitio[0]:sitio[0] + sitio[1]])


def country_names(data: bytes) -> dict[int, list[str]]:
    """`{código de idioma: [nombre por código de país]}`."""
    out: dict[int, list[str]] = {}
    for nombre, sitio in entradas(data).items():
        familia, _, num = nombre.partition(".")
        if familia.upper() != "PAISES" or not num.isdigit():
            continue
        out[int(num)] = _lee(data, sitio)[1]
    return out


def name_pools(data: bytes) -> dict[int, dict]:
    """`{código de país: {"nombres": [...], "apellidos": [...]}}`."""
    out: dict[int, dict] = {}
    for nombre, sitio in entradas(data).items():
        familia, _, num = nombre.partition(".")
        clave = FAMILIAS.get(familia.upper())
        if not clave or not num.isdigit():
            continue
        out.setdefault(int(num), {})[clave] = _lee(data, sitio)[1]
    return out


def _patch_pak(data: bytes, nuevos: dict[str, bytes]) -> bytes:
    """Sustituye entradas de un `PAK_` ANEXANDO el bloque nuevo y apuntando su cabecera.

    Es el mismo camino que ya usamos para los gráficos: no se reescribe el resto del
    fichero ni se recolocan los offsets de los demás, que son absolutos."""
    import struct
    b = bytearray(data)
    for nombre, init, largo, hdr in _PAK.index_var(data):
        corto = nombre.replace("/", "\\").split("\\")[-1].upper()
        blob = nuevos.get(corto)
        if blob is None or blob == bytes(data[init:init + largo]):
            continue
        sitio = len(b)
        b += blob
        struct.pack_into("<III", b, hdr, sitio, len(blob), len(blob))
    return bytes(b)


def _patch(data: bytes, nuevos: dict[str, bytes]) -> bytes:
    if not nuevos:
        return data
    if es_pak(data):
        return _patch_pak(data, nuevos)
    return _TX.patch_container(data, nuevos)


def patch_country_names(data: bytes, langs: dict) -> bytes:
    """Contenedor con los nombres de país cambiados. `langs` = `{idioma: [nombres]}`.

    La lista es POSICIONAL y **nunca se acorta**: el juego indexa por posición, así que
    quitar una entrada le correría todos los países siguientes."""
    ent = entradas(data)
    nuevos: dict[str, bytes] = {}
    for idioma, textos in (langs or {}).items():
        sitio = ent.get(f"PAISES.{int(idioma)}")
        if not sitio or textos is None:
            continue
        original = data[sitio[0]:sitio[0] + sitio[1]]
        ident, viejos = _lee(data, sitio)
        lista = [str(t) if t is not None else v for t, v in zip(textos, viejos)]
        lista += viejos[len(lista):]
        blob = _TX.write_list(ident, lista)
        if blob != original:
            nuevos[f"PAISES.{int(idioma)}"] = blob
    return _patch(data, nuevos)


def patch_pools(data: bytes, pools: dict) -> bytes:
    """Contenedor con los pozos de nombres cambiados.
    `pools` = `{país: {"nombres": [...], "apellidos": [...]}}`."""
    ent = entradas(data)
    nuevos: dict[str, bytes] = {}
    for pais, campos in (pools or {}).items():
        for clave, familia in (("nombres", "NOMBRES"), ("apellidos", "APELLIDO")):
            textos = (campos or {}).get(clave)
            if textos is None:
                continue
            nombre = f"{familia}.{int(pais)}"
            sitio = ent.get(nombre)
            if not sitio:
                continue            # no se INVENTAN pozos que esta edición no trae
            original = data[sitio[0]:sitio[0] + sitio[1]]
            ident = _lee(data, sitio)[0]
            blob = _TX.write_list(ident, [str(t) for t in textos if str(t).strip()])
            if blob != original:
                nuevos[nombre] = blob
    return _patch(data, nuevos)
