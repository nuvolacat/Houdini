"""Codec IFF ILBM y contenedor `PCFTEX*.DAT`/`LGR.DAT` del launcher de PC Fútbol 4.0.

Verifica el round-trip: decodificar cada imagen y re-inyectarla debe re-decodificar
pixel-perfecto, y (salvo alguna que no comprima tan ajustado como el original) conservar
la longitud del contenedor. Se salta si no está el gamedata (gitignored).
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from houdini_engine.codec import ilbm
from houdini_engine.formats import pcf4_tex as TEX

_GAMEDATA = Path(__file__).resolve().parents[2] / "gamedata"
_CANDIDATES = ["pcf4/PCFTEX4.DAT", "pcf4/LGR.DAT"]
_AVAIL = [c for c in _CANDIDATES if (_GAMEDATA / c).exists()]
skip_no_files = pytest.mark.skipif(not _AVAIL, reason="contenedores ILBM de PCF4 no disponibles")


def _pixels(png: bytes):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    return im.tobytes(), im.size


@skip_no_files
@pytest.mark.parametrize("rel", _AVAIL)
def test_forms_detected(rel):
    data = (_GAMEDATA / rel).read_bytes()
    imgs = TEX.list_images(data)
    assert len(imgs) >= 10
    assert all(im["w"] > 0 and im["h"] > 0 for im in imgs)


@skip_no_files
@pytest.mark.parametrize("rel", _AVAIL)
def test_roundtrip_pixel_perfect(rel):
    data = (_GAMEDATA / rel).read_bytes()
    imgs = TEX.list_images(data)
    inplace = 0
    for im in imgs:
        i = im["i"]
        png = TEX.image_png(data, i)
        new = TEX.replace_image(data, i, png)
        # re-inyectar la MISMA imagen no debe cambiar ningún píxel
        (pa, sa), (pb, sb) = _pixels(png), _pixels(TEX.image_png(new, i))
        assert sa == sb == (im["w"], im["h"])
        assert pa == pb, f"round-trip alteró píxeles en {rel}#{i}"
        if len(new) == len(data):
            inplace += 1
        # el contenedor reconstruido debe seguir teniendo el mismo nº de imágenes
        assert len(TEX.list_images(new)) == len(imgs)
    # la gran mayoría cabe in-place (longitud del contenedor intacta)
    assert inplace >= len(imgs) - 6


@skip_no_files
def test_build_form_valid():
    """Un FORM construido desde cero se re-decodifica con el tamaño correcto."""
    rel = _AVAIL[0]
    data = (_GAMEDATA / rel).read_bytes()
    off, size = ilbm.iter_forms(data)[0]
    info = ilbm.parse_form(data, off, size)
    body = ilbm.encode_body(TEX.image_png(data, 0), info["w"], info["h"],
                            info["nplanes"], _pal := [(info["cmap"][k * 3], info["cmap"][k * 3 + 1],
                            info["cmap"][k * 3 + 2]) for k in range(len(info["cmap"]) // 3)], info["comp"])
    form = ilbm.build_form(info["w"], info["h"], info["nplanes"], info["cmap"], body, info["comp"])
    im = ilbm.decode(form, 0, len(form))
    assert im.size == (info["w"], info["h"])
