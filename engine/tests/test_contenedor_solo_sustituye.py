"""Reempaquetar un contenedor sin CAMBIARLE LA FORMA DEL ÍNDICE.

Contexto (1-sep-2026). Las fotos de entrenador no pueden ir en ficheros sueltos: el
`manager.exe` de v5/6 tiene ruta suelta para escudos, banderas, fotos, estadios y fondos, pero
para `MINIENTR`/`BIGENTR` no hay ninguna — solo las busca dentro del contenedor. Al meterlas
ahí, `patch_container` hacía dos cosas muy distintas según el caso:

  · SUSTITUIR una imagen que ya existe: se anexa el blob al final y se repuntan sus ocho bytes
    de offset y tamaño. El índice queda idéntico y el juego lo recorre igual que siempre.
  · AÑADIR una que no existe: hay que convertir el fin del índice (`05`) en un salto (`04`) a
    una sección nueva. Nuestro lector lo sigue, pero que el del JUEGO lo siga es una
    suposición, y está marcada como pendiente de validar desde que se escribió.

Los mods que crashean al cargar la base traían justo eso: 16 entradas nuevas en `MINIENTR` y 11
en `BIGENTR`. Así que la descarga pasa a usar el modo prudente. Este test fija las dos mitades:
que sustituir funciona y que en ese modo el índice no cambia ni un byte.
"""
import os
import struct

import pytest

from houdini_engine.formats import imagenes_pkf as IM

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _contenedor():
    for edicion in ("pcf6", "pcf6oro", "pcf5oro"):
        p = os.path.join(RAIZ, "gamedata", edicion, "MINIENTR.PKF")
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
    pytest.skip("sin MINIENTR.PKF en gamedata")


def _indice(data):
    """La forma del índice: (tag, nombre) de cada registro. Es lo que recorre el juego."""
    return [(tag, IM._entry_name(data, pos) if tag == 0x02 else "")
            for pos, tag in IM._index_walk(data)]


def _blob(data, nombre):
    for pos, tag in IM._index_walk(data):
        if tag == 0x02 and IM._entry_name(data, pos).upper() == nombre.upper():
            off, size = struct.unpack_from("<II", data, pos + 26)
            return data[off:off + size]
    raise AssertionError(nombre)


def test_entries_lista_los_nombres_reales():
    data = _contenedor()
    nombres = IM.entries(data)
    assert nombres, "el contenedor de fotos de entrenador no está vacío"
    # `E` + prefijo de dos cifras + puntero de entrenador de CINCO (los escudos usan cuatro)
    for n in nombres:
        cuerpo, _, ext = n.partition(".")
        assert len(cuerpo) == 8 and cuerpo[0] == "E" and cuerpo[1:].isdigit(), n
        assert ext.upper() in ("BMP", "GIF"), n


def test_la_extension_no_se_puede_dar_por_supuesta():
    """EL FALLO QUE ROMPÍA 6.0 ORIGINAL. Escribíamos siempre `E96NNNNN.BMP`, pero medido en
    `gamedata` la convención cambia por edición y por contenedor:

        5.0 / 5.0 Oro / 6.0 Oro   MINIENTR y BIGENTR   .BMP, prefijo 96
        6.0 original              BIGENTR              .BMP, prefijo 96
        6.0 original              MINIENTR             .GIF, prefijos 95 Y 96  (104 fotos)

    O sea que en 6.0 original le metíamos al MINIENTR entradas NUEVAS con una extensión que
    el juego nunca pide y un formato que ahí no usa. Por eso el nombre se lee del contenedor.
    """
    combinaciones = set()
    for ed in ("pcf5", "pcf5oro", "pcf6", "pcf6oro"):
        for cont in ("MINIENTR", "BIGENTR"):
            ruta = os.path.join(RAIZ, "gamedata", ed, f"{cont}.PKF")
            if not os.path.exists(ruta):
                continue
            with open(ruta, "rb") as f:
                nombres = IM.entries(f.read())
            for n in nombres:
                combinaciones.add((n.rsplit(".", 1)[-1].upper(), n[1:3]))
    if not combinaciones:
        pytest.skip("sin bases de v5/6 en gamedata")
    assert ("GIF", "95") in combinaciones, "el MINIENTR de 6.0 original son GIF con prefijo 95"
    assert ("BMP", "96") in combinaciones, "y el resto BMP con prefijo 96"


def test_sustituir_no_toca_la_forma_del_indice():
    """LA REGRESIÓN: en modo prudente el juego recorre exactamente el mismo índice."""
    data = _contenedor()
    antes = _indice(data)
    victima = IM.entries(data)[0]
    otro = _blob(data, IM.entries(data)[1])
    salida = IM.patch_container(data, {victima: otro}, permitir_nuevas=False)
    assert _indice(salida) == antes
    assert _blob(salida, victima) == otro, "la imagen sí se cambió"


def test_en_modo_prudente_las_nuevas_se_ignoran():
    data = _contenedor()
    nueva = "E9799999.BMP"
    assert nueva not in {n.upper() for n in IM.entries(data)}
    salida = IM.patch_container(data, {nueva: _blob(data, IM.entries(data)[0])},
                                permitir_nuevas=False)
    assert salida == data, "sin nada que sustituir, el fichero sale intacto"


def test_el_modo_de_ampliar_sigue_existiendo():
    """No se borra: hace falta para los contenedores donde sí está validado, y volverá aquí
    en cuanto se pruebe el salto en la VM."""
    data = _contenedor()
    nueva = "E9799999.BMP"
    salida = IM.patch_container(data, {nueva: _blob(data, IM.entries(data)[0])})
    assert nueva in {n.upper() for n in IM.entries(salida)}
    assert len(_indice(salida)) > len(_indice(data)), "el índice crece, que es el riesgo"


def test_las_imagenes_previas_sobreviven_en_los_dos_modos():
    data = _contenedor()
    originales = {n: _blob(data, n) for n in IM.entries(data)[:20]}
    victima = IM.entries(data)[0]
    for kw in ({"permitir_nuevas": False}, {}):
        salida = IM.patch_container(data, {"E9799999.BMP": originales[victima]}, **kw)
        for n, b in originales.items():
            assert _blob(salida, n) == b, f"{n} se rompió con {kw}"


# --- la CABECERA de la imagen, que es lo que de verdad lee el juego -----------------------
def _miembros(ruta):
    with open(ruta, "rb") as f:
        d = f.read()
    out = {}
    for pos, tag in IM._index_walk(d):
        if tag == 0x02:
            off, size = struct.unpack_from("<II", d, pos + 26)
            out[IM._entry_name(d, pos)] = d[off:off + size]
    return out


def _ruta(ed, cont):
    p = os.path.join(RAIZ, "gamedata", ed, f"{cont}.PKF")
    if not os.path.exists(p):
        pytest.skip(f"sin {ed}/{cont} en gamedata")
    return p


def test_cada_contenedor_es_coherente_con_su_variante():
    """El dato de partida. Medido en `gamedata`, un contenedor NO mezcla cabeceras:

        5.0 original                     `DM` + cabecera de 40 (BITMAPINFOHEADER)
        5.0 Oro / 6.0 / 6.0 Oro          `BM` + cabecera de 12 (BITMAPCOREHEADER)

    Las dos van sin tabla de paleta: la pone el juego."""
    esperado = {"pcf5": (b"DM", 40), "pcf5oro": (b"BM", 12),
                "pcf6": (b"BM", 12), "pcf6oro": (b"BM", 12)}
    vistos = 0
    for ed, (magia, bisize) in esperado.items():
        for cont in ("BIGENTR", "NANOESC", "BANDERAS"):
            p = os.path.join(RAIZ, "gamedata", ed, f"{cont}.PKF")
            if not os.path.exists(p):
                continue
            variantes = {(b[:2], struct.unpack_from("<I", b, 14)[0])
                         for b in _miembros(p).values()}
            assert variantes == {(magia, bisize)}, f"{ed}/{cont}: {variantes}"
            vistos += 1
    if not vistos:
        pytest.skip("sin bases de v5/6 en gamedata")


@pytest.mark.parametrize("edicion,contenedor", [("pcf6", "BIGENTR"),        # BM + 12
                                                ("pcf6oro", "MINIENTR"),    # BM + 12
                                                ("pcf5", "MINIENTR")])      # DM + 40
def test_ida_y_vuelta_byte_a_byte(edicion, contenedor):
    """LA REGRESIÓN. Sacar la imagen del contenedor y volver a meterla tiene que devolver
    EXACTAMENTE los mismos bytes. Antes no: se escribía siempre `DM`+40, así que en las tres
    ediciones que usan `BM`+12 cada foto de entrenador que tocábamos quedaba ilegible para el
    juego —incluidas las que solo se estaban actualizando."""
    from houdini_engine.codec.image import _palette
    paleta = _palette()
    iguales = 0
    for nombre, blob in list(_miembros(_ruta(edicion, contenedor)).items())[:25]:
        bmp = IM.dm_to_bmp(blob, paleta)
        assert IM.bmp_to_member(bmp, modelo=blob) == blob, nombre
        iguales += 1
    assert iguales, "no se probó ninguna imagen"


def test_sin_modelo_se_mantiene_lo_de_siempre():
    """`bmp_to_dm` sigue existiendo y sigue dando la variante `DM`: es la de 5.0 original y
    hay código que la usa."""
    from houdini_engine.codec.image import _palette
    paleta = _palette()
    blob = next(iter(_miembros(_ruta("pcf5", "MINIENTR")).values()))
    assert IM.bmp_to_dm(IM.dm_to_bmp(blob, paleta))[:2] == b"DM"


def test_la_variante_BM_de_cabecera_larga_tambien_se_respeta():
    """Apertura 98 y el MINIENTR de PCF7 usan `BM` con cabecera de 40: es una tercera
    combinación, y la magia tiene que salir del modelo, no de una constante."""
    from houdini_engine.codec.image import _palette
    ruta = os.path.join(RAIZ, "gamedata", "apertura98", "NANOESC.PKF")
    if not os.path.exists(ruta):
        pytest.skip("sin la base de Apertura 98")
    blob = next(iter(_miembros(ruta).values()))
    assert blob[:2] == b"BM" and struct.unpack_from("<I", blob, 14)[0] == 40
    assert IM.bmp_to_member(IM.dm_to_bmp(blob, _palette()), modelo=blob) == blob


def test_member_blob_sirve_de_modelo():
    with open(_ruta("pcf6", "BIGENTR"), "rb") as f:
        data = f.read()
    modelo = IM.member_blob(data)
    assert modelo and modelo[:2] == b"BM"
    assert IM.member_blob(data, IM.entries(data)[3]) == list(_miembros(_ruta("pcf6", "BIGENTR")).values())[3]
    assert IM.member_blob(data, "NO_EXISTE.BMP") is None
