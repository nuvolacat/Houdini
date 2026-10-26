"""Tests del motor DBC: fichero por equipo + operaciones estructurales."""
from pathlib import Path

import pytest

from houdini_engine.formats import block as B
from houdini_engine.formats import dbc as D
from houdini_engine.formats import equipos_pkf as E

_MATERIAL = Path(__file__).resolve().parents[2] / "gamedata" / "material-v56"
_FILES = {
    "5.0": _MATERIAL / "PC Fútbol 5.0/DBDAT/EQUIPOS.PKF",
    "6.0": _MATERIAL / "PC Fútbol 6.0/Dbdat/EQ022022.PKF",
}
_available = [(v, p) for v, p in _FILES.items() if p.exists()]
skip_no_files = pytest.mark.skipif(not _available, reason="ficheros del juego no disponibles")


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_write_dbc_all_teams(ver, path):
    """El DBC de cada equipo = su bloque con FE06 en lugar del puntero."""
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    sigs = sorted(t.sig_off for t in pf.teams)
    for tid, t in enumerate(pf.teams):
        if not t.players:
            continue
        blk = D.block_for_team(pf, tid)
        out = D.write_dbc(blk, con_textos=True)
        nxt = min([s for s in sigs if s > t.sig_off], default=len(data))
        original = data[t.sig_off:nxt].rstrip(b"\x00") if blk.trailing else data[t.sig_off:nxt]
        expect = bytearray(blk.prefix + b"".join(p.serialize() for p in blk.players))
        expect[36:38] = D.DBC_MARKER
        assert out == bytes(expect) + b"\x00" * D.DBC_PADDING
        assert out[:36] == data[t.sig_off:t.sig_off + 36]
        assert out[36:38] == b"\xff\xff"
        # el resto del prefijo intacto
        assert out[38:len(blk.prefix)] == data[t.sig_off + 38:t.sig_off + len(blk.prefix)]


@skip_no_files
@pytest.mark.parametrize("ver,path", _available)
def test_parse_dbc_roundtrip(ver, path):
    """parse_dbc(write_dbc(bloque)) reconstruye los mismos jugadores."""
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    tested = 0
    for tid, t in enumerate(pf.teams):
        if not t.players or tested >= 25:
            continue
        blk = D.block_for_team(pf, tid)
        blk2 = D.parse_dbc(D.write_dbc(blk, con_textos=True), path.name)
        assert len(blk2.players) == len(blk.players), t.short_name
        for a, b in zip(blk.players, blk2.players):
            assert a.serialize() == b.serialize()
        tested += 1
    assert tested >= 20


@skip_no_files
def test_structural_ops():
    path = _FILES["5.0"]
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    tid = next(i for i, t in enumerate(pf.teams) if t.complete and len(t.players) > 15)
    blk = D.block_for_team(pf, tid)
    n0 = len(blk.players)
    used = {p.pointer for p in pf.players}

    # añadir un delantero con nombre largo sin límite
    ptr = B.free_pointer(used, team_pointer=4)
    p = B.new_player(pointer=ptr, number=39, short="Nuevo Fichaje",
                     long="Delantero Con Nombre Larguísimo De Verdad", demarcation=9,
                     ptype=3, country=22, foreign=False)
    idx = B.add_player(blk, p)
    assert len(blk.players) == n0 + 1
    # quedó al final (delantero) y el orden por tipo se mantiene
    types = [x.ptype for x in blk.players]
    assert types == sorted(types)

    # un portero se inserta al principio del grupo de porteros
    ptr2 = B.free_pointer(used | {ptr})
    g = B.new_player(pointer=ptr2, number=40, short="Portero Nuevo",
                     long="Portero Nuevo", demarcation=1, ptype=0, country=22, foreign=False)
    B.add_player(blk, g)
    types = [x.ptype for x in blk.players]
    assert types == sorted(types)

    # puntero repetido -> error
    with pytest.raises(ValueError):
        B.add_player(blk, B.new_player(pointer=ptr, number=41, short="Dup", long="Dup",
                                       demarcation=9, ptype=3, country=22, foreign=False))

    # el DBC resultante parsea con los jugadores nuevos y sus datos
    blk2 = D.parse_dbc(D.write_dbc(blk, con_textos=True), path.name)
    assert len(blk2.players) == n0 + 2
    nuevo = next(x for x in blk2.players if x.pointer == ptr)
    assert nuevo.short_name == "Nuevo Fichaje"
    assert nuevo.long_name == "Delantero Con Nombre Larguísimo De Verdad"
    assert nuevo.ptype == 3

    # quitar
    B.remove_player(blk, idx)
    assert len(blk.players) == n0 + 1

    # límite de plantilla
    while len(blk.players) < B.MAX_PLAYERS:
        used2 = {x.pointer for x in blk.players} | used
        B.add_player(blk, B.new_player(pointer=B.free_pointer(used2), number=1,
                                       short="Relleno", long="Relleno", demarcation=9,
                                       ptype=3, country=22, foreign=False))
    with pytest.raises(ValueError):
        B.add_player(blk, B.new_player(pointer=65000, number=1, short="Sobra", long="Sobra",
                                       demarcation=9, ptype=3, country=22, foreign=False))


@skip_no_files
def test_set_field_and_rating():
    path = _FILES["5.0"]
    pf = E.parse(path.read_bytes(), path.name)
    tid = next(i for i, t in enumerate(pf.teams) if t.complete and t.players)
    blk = D.block_for_team(pf, tid)
    p = blk.players[0]
    p.set_field("height", 199)
    p.set_field("birth_year", 1969)
    p.set_field("demarcation0", 9)
    p.set_rating(3, 97)
    q = D.parse_dbc(D.write_dbc(blk), path.name).players[0]
    assert q.fixed[16] == 199
    assert q.fixed[14] | (q.fixed[15] << 8) == 1969
    assert q.fixed[2] == 9
    assert q.medias[3] == 97


def test_free_pointer():
    assert B.free_pointer(set(), team_pointer=4) == 151
    assert B.free_pointer({151, 152}, team_pointer=4) == 153
    used = set(range(151, 201))
    # rango agotado -> primer hueco global BAJO EL TOPE del juego (no max+1:
    # punteros altos crashean MANAGER.EXE al cargar los DBC)
    assert B.free_pointer(used, team_pointer=4) == 1
    assert B.free_pointer({1, 2, 3}) == 4
    # equipos foráneos con puntero alto: su rango canónico (>19999) se salta
    assert B.free_pointer({1}, team_pointer=401) == 2
    assert B.free_pointer(set(range(1, 19999)), team_pointer=401) == 19999
    assert B.free_pointer(set(range(1, 20000)), team_pointer=401) == 20000  # franja 20000-22060


def test_dbc_names():
    assert D.dbc_filename("97", 4) == "EQ970004.DBC"
    assert D.dbc_folder("EQ030022.PKF") == "EQ030022"
    assert D.dbc_folder("Equipos.pkf") == "EQUIPOS"


# --- los textos de base de datos NO van en el DBC (como PCx-Utils) ---

@pytest.mark.parametrize("ver,path", _available)
def test_el_dbc_sale_sin_los_textos_de_bbdd(ver, path):
    """El escritor de referencia de la comunidad (PCx-Utils, `pcf-v6-bytesteams`) vacía todos
    los textos de base de datos antes de volcar cada DBC. Y los números explican por qué: son el
    **85% del fichero** — 42,7 KB de media frente a 6,6 KB sin ellos.

    Importa cuando hay muchos: el ajuste masivo de medias marca ~478 equipos y el juego los lee
    TODOS al crear liga. 21 MB de golpe en un motor de 1997 frente a 3,2 MB. Un usuario reportó que
    6.0 Oro se cerraba justo ahí, mientras que los amistosos —que no leen estos ficheros— le
    funcionaban.

    Los textos no se pierden: siguen en el fichero principal, que también va en la descarga.
    """
    pf = E.parse(path.read_bytes(), path.name)
    medido = 0
    for tid, t in enumerate(pf.teams):
        if not t.players or medido >= 5:
            continue
        blk = D.block_for_team(pf, tid)
        if not any(getattr(p, "db_strings", None) for p in blk.players):
            continue          # equipo foráneo: no tiene textos que quitar
        con = D.write_dbc(blk, con_textos=True)
        sin = D.write_dbc(blk)
        assert len(sin) < len(con), f"{t.short_name}: el DBC no adelgaza"
        # y el bloque ORIGINAL no se toca: se serializa una copia
        assert any(getattr(p, "db_strings", None) for p in blk.players), \
            "write_dbc ha vaciado los textos del bloque de la sesión"
        medido += 1
    assert medido, "no se midió ningún equipo con textos"
