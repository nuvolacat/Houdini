"""Tests de humo de Fase 0: codec de texto y datos de referencia."""
from houdini_engine import refdata
from houdini_engine.codec import text


def test_text_roundtrip_ascii():
    for s in ["Vucevic", "Manolo HIERRO ", "Real Madrid C.F.", "1234567890", ""]:
        assert text.decode(text.encode(s)) == s


def test_text_xor_key():
    # 'A' (0x41) ^ 0x61 = 0x20
    assert text.encode("A") == bytes([0x20])
    assert text.decode(bytes([0x20])) == "A"


def test_lenprefixed_roundtrip():
    blob = text.encode_lenprefixed("Hierro")
    assert blob[0] == 6 and blob[1] == 0x00
    value, nxt = text.decode_lenprefixed(blob, 0)
    assert value == "Hierro" and nxt == len(blob)


def test_refdata_countries():
    c = refdata.countries()
    assert len(c) == 206
    assert any(x["name"] == "España" for x in c)


def test_refdata_teams_tactics_kits():
    assert len(refdata.teams()) == 1378
    assert len(refdata.tactics()) == 15
    assert len(refdata.kits()) == 53
