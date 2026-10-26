"""Round-trip byte-perfecto del bloque de equipo completo (base para DBC)."""
from pathlib import Path

import pytest

from houdini_engine.formats import block as B
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
def test_all_blocks_roundtrip(ver, path):
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    sigs = sorted(t.sig_off for t in pf.teams)
    tested = ok = 0
    for t in pf.teams:
        if not t.players:
            continue
        first = min(p.offset for p in t.players) - 1
        nxt = min([s for s in sigs if s > t.sig_off], default=len(data))
        foreign = data[t.sig_off + 41] == 1
        blk = B.parse_block(data, t.sig_off, nxt, first, foreign)
        assert blk.serialize() == data[t.sig_off:nxt], f"{ver}: {t.short_name} no round-trip"
        ok += 1
        tested += 1
    assert tested > 100 and ok == tested


@skip_no_files
def test_player_name_edit():
    path = _FILES["5.0"]
    if not path.exists():
        pytest.skip("5.0 no disponible")
    data = path.read_bytes()
    pf = E.parse(data, path.name)
    t = next(x for x in pf.teams if x.complete and x.players)
    sigs = sorted(x.sig_off for x in pf.teams)
    first = min(p.offset for p in t.players) - 1
    nxt = min([s for s in sigs if s > t.sig_off], default=len(data))
    blk = B.parse_block(data, t.sig_off, nxt, first, False)
    # cambiar un nombre a algo MÁS LARGO que el original (posible en DBC)
    orig_len = len(blk.serialize())
    blk.players[0].set_short("Nombre Muy Largo Sin Limite")
    assert len(blk.serialize()) > orig_len  # el bloque crece sin problema
