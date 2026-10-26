"""Pantallas PKF de PC Fútbol 7 (Recursos/Img/DAT): índice, paletas, render e import in-place."""
from pathlib import Path

import pytest

from houdini_engine.formats import pantallas_pkf as PP

_REC = Path(__file__).resolve().parents[2] / "gamedata" / "FUTBOL7" / "Recursos.pkf"
_DAT = Path(__file__).resolve().parents[2] / "gamedata" / "FUTBOL7" / "DAT.PKF"
_skip = not (_REC.exists() and _DAT.exists())


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_index_and_names():
    ents = PP.entries(_REC.read_bytes())
    assert len(ents) > 500                       # cientos de pantallas
    names = {e.name for e in ents}
    assert "FONDO7.BMP" in names                 # fondo de la portada
    assert any(e.name.startswith("BARRA") for e in ents)


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_palettes_riff():
    pals = PP.palettes(_DAT.read_bytes())
    assert "MENU" in pals and len(pals["MENU"]) == 768   # 256 × RGB


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_render_and_inplace_roundtrip():
    data = _REC.read_bytes()
    pal = PP.palettes(_DAT.read_bytes())["MENU"]
    fondo = next(e for e in PP.entries(data) if e.name == "FONDO7.BMP")
    blob = data[fondo.off:fondo.off + fondo.size]
    assert PP.bmp_dims(blob) == (640, 480)
    png = PP.to_png(blob, pal)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    # import: reimportar el propio PNG debe dar un blob del MISMO tamaño (encaja in-place)
    new_blob = PP.replace_bmp(blob, png, pal)
    assert len(new_blob) == fondo.size
    out = PP.repack_inplace(data, {fondo.off: new_blob})
    assert len(out) == len(data)                 # fichero idéntico en tamaño
    assert len(PP.entries(out)) == len(PP.entries(data))   # índice intacto


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_repack_noop_identical():
    data = _REC.read_bytes()
    assert PP.repack_inplace(data, {}) == data   # sin cambios → idéntico


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_auto_palette_picks_sensible():
    """Auto-mapeo: cada BMP se ve mejor con SU paleta real (embebida en un GIF), no con MENU fija.
    FONDO7 (foto de portada) debe caer en una paleta tipo MENU; PCFUTBOL (logo blanco) en otra."""
    data = _REC.read_bytes()
    cat = PP.palette_catalog([data, _DAT.read_bytes()])
    assert len(cat) > 5                          # DAT (4) + varias de los GIF
    ents = {e.name: e for e in PP.entries(data)}
    fondo = ents["FONDO7.BMP"]
    logo = ents["PCFUTBOL.BMP"]
    pf = PP.best_palette(data[fondo.off:fondo.off + fondo.size], cat)
    pl = PP.best_palette(data[logo.off:logo.off + logo.size], cat)
    assert pf and pl
    # la paleta buena del logo NO es la buena del fondo (usan pantallas/paletas distintas)
    assert pf[0] != pl[0]


@pytest.mark.skipif(_skip, reason="faltan los contenedores de PCF7 en gamedata")
def test_entradas_anonimas_recursos():
    """Las entradas tag 0x03 (offset+tamaño SIN nombre) son los fondos 640×480 de las
    portadas (PC CALCIO 7 entre ellas). Antes el recorredor moría en la primera y eran
    invisibles — el bug del foro «faltan fondos» (2026-09-03)."""
    ents = PP.entries(_REC.read_bytes())
    anon = [e for e in ents if e.name.startswith("SIN_NOMBRE_")]
    assert len(anon) == 3
    data = _REC.read_bytes()
    for e in anon:
        assert e.size == 307228                          # 640×480 + cabecera CORE
        assert data[e.off:e.off + 2] == b"BM"
    # y las anonimas NO desplazan los idx de las entradas con nombre
    assert [e.idx for e in anon] == [1156, 1157, 1158]


def test_entrada_anonima_sintetica():
    """Un contenedor mínimo con una entrada normal + una anónima + terminador."""
    import struct
    blob_a, blob_b = b"BM" + b"\x01" * 30, b"BM" + b"\x02" * 40
    header = b"\x01" + b"\x00" * 231
    # índice: entrada 0x02 (nombre cifrado) + entrada 0x03 + fin
    off_idx = len(header)
    off_a = off_idx + 38 + 9 + 1
    off_b = off_a + len(blob_a)
    nombre = bytes(b ^ k for b, k in zip(b"UNO.BMP".ljust(20, b"\x00"), PP._KEY))
    e2 = (b"\x02" + nombre + b"\x00" * 5 + struct.pack("<II", off_a, len(blob_a))
          + b"\x00" * 4)                                  # hasta los 38 B de la entrada
    e3 = b"\x03" + struct.pack("<II", off_b, len(blob_b))
    data = header + e2 + e3 + b"\x00" + blob_a + blob_b
    ents = PP.entries(data)
    assert [(e.name, e.off, e.size) for e in ents] == [
        ("UNO.BMP", off_a, len(blob_a)),
        ("SIN_NOMBRE_1.BMP", off_b, len(blob_b)),
    ]
