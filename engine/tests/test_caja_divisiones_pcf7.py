"""PCF7: «Respetar la caja de la base en Segunda y Segunda B»."""
import os
from pathlib import Path

import pytest

from houdini_engine.formats import manager as M

EXE = Path(os.environ.get("HOUDINI_GAMEDATA", Path(__file__).resolve().parents[2] / "gamedata")) / "FUTBOL7" / "MANAGER.EXE"


@pytest.mark.skipif(not EXE.exists(), reason="sin el MANAGER.EXE de PCF7")
def test_parche_ida_y_vuelta():
    orig = EXE.read_bytes()
    regla = {r["key"]: r for r in M.restrictions_read(orig)}["caja_divisiones"]
    assert regla["available"] and regla["state"] == "off"
    b = bytearray(orig)
    assert M.restrictions_write(b, {"caja_divisiones": True}) == 1
    assert b[0xBA462:0xBA468] == bytes.fromhex("81F9FFFF0000")      # cmp ecx, 0xFFFF (2ªB)
    assert b[0xBA4AD:0xBA4B3] == bytes.fromhex("81F9FFFF0000")      # cmp ecx, 0xFFFF (Segunda)
    assert sum(x != y for x, y in zip(b, orig)) == 4                 # nada más
    assert {r["key"]: r for r in M.restrictions_read(bytes(b))}["caja_divisiones"]["state"] == "on"
    assert M.restrictions_write(b, {"caja_divisiones": False}) == 1
    assert bytes(b) == orig


def test_no_sale_en_otras_ediciones():
    falso = bytes(2662400)                                          # tamaño de 6.0 Oro
    claves = {r["key"] for r in (M.restrictions_read(falso) or [])}
    assert "caja_divisiones" not in claves


def test_manager_ajeno_no_se_toca():
    b = bytearray(4939776)                                           # tamaño de PCF7, otros bytes
    assert M.restrictions_write(b, {"caja_divisiones": True}) == 0
    assert not any(b)
