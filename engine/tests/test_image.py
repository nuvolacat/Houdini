"""Tests del códec de imagen (escudos/fotos)."""
import json
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from houdini_engine.codec import image as I

_REF = Path(__file__).resolve().parents[1] / "houdini_engine" / "refdata"


def _sample_png() -> bytes:
    im = Image.new("RGB", (200, 200), (255, 255, 255))
    ImageDraw.Draw(im).ellipse((30, 30, 170, 170), fill=(200, 0, 0))
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def test_escudo_sizes_and_format():
    esc = I.escudo_set(_sample_png())
    assert set(esc) == {"nano", "mini", "ridi", "big"}
    for name, size in I.ESCUDO_SIZES.items():
        img = Image.open(BytesIO(esc[name]))
        assert img.format == "BMP" and img.mode == "P" and img.size == size


def test_palette_matches_game():
    esc = I.escudo_set(_sample_png())
    game = json.loads((_REF / "palette_escudo.json").read_text())[:768]
    assert Image.open(BytesIO(esc["nano"])).getpalette()[:768] == game


def test_photo_and_preview():
    bmp = I.photo_bmp(_sample_png())
    img = Image.open(BytesIO(bmp))
    assert img.mode == "P" and img.size == I.PHOTO_SIZE
    png = I.game_bmp_to_png(bmp)
    assert Image.open(BytesIO(png)).format == "PNG"


def test_tamanos_de_escudo_son_los_del_juego():
    """Los tamaños con los que generamos escudos deben ser los que usa el juego.

    Hasta 2026-08-20 `nano` iba a 25×32 y `ridi` a 19×21: valores tomados de los scripts
    de PCx-Utils que no aparecen en NINGUNA de las ~4.900 imágenes originales de v5/6.
    Los de aquí salen de MEDIR los contenedores de las ocho ediciones v5/6:
    NANOESC 24×32 (99,5%), MINIESC 48×64 (99,5%), RIDIESC 17×20 (4.900 de 4.900).
    """
    assert I.ESCUDO_SIZES["nano"] == (24, 32)
    assert I.ESCUDO_SIZES["mini"] == (48, 64)
    assert I.ESCUDO_SIZES["ridi"] == (17, 20)


def test_tamanos_de_escudo_de_pcf7():
    """PCF7 es OTRA familia y se mide aparte: 294 escudos de su NANOESC/MINIESC/RIDIESC
    dan 24×32, 48×64 y 17×20. Coincide con v5/6, pero por medición propia — no se da por
    heredado (v5/6 y 7 se parecen y NO son lo mismo)."""
    from houdini_engine.codec import pcf7_image as P7
    assert P7.ESCUDO_SIZES["nano"] == (24, 32)
    assert P7.ESCUDO_SIZES["mini"] == (48, 64)
    assert P7.ESCUDO_SIZES["ridi"] == (17, 20)
