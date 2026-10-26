"""El u32 de los bloques DMLT es la suma de longitudes + nº de textos, no un id opaco."""
import glob
import os

import pytest

from houdini_engine.formats import textos_pkf as T

FICHEROS = sorted(glob.glob("gamedata/pcf6*/textos.pkf")) or sorted(
    glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "gamedata", "pcf6*", "textos.pkf")))


def test_write_list_recalcula_la_cuenta():
    textos = ["García", "Fernández", "Ruiz"]
    blob = T.write_list(999999, textos)          # el ident que se pasa da igual
    cuenta, leidos = T.read_list(blob)
    assert leidos == textos
    assert cuenta == sum(len(t) for t in textos) + len(textos) == 22


def test_la_cuenta_va_en_BYTES_no_en_caracteres():
    """Un texto con un carácter fuera de latin-1 no debe descuadrar la cuenta."""
    blob = T.write_list(0, ["Muñoz"])
    cuenta, _ = T.read_list(blob)
    # el bloque son 12 de cabecera + 2 de longitud + los bytes del texto
    assert cuenta == len(blob) - 12 - 2 + 1


def test_round_trip_conserva_la_cuenta_del_juego():
    """Reescribir una lista sin tocarla debe devolver el mismo valor que traía el fichero."""
    if not FICHEROS:
        pytest.skip("sin gamedata")
    for f in FICHEROS:
        d = open(f, "rb").read()
        for nombre, (off, size) in T.entries(d).items():
            cuenta, textos = T.read_list(d[off:off + size])
            assert T.read_list(T.write_list(0, textos))[0] == cuenta, f"{f}:{nombre}"
