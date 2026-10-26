"""Pantallas del launcher/actualizador de PC Fútbol 4.0 — contenedores ILBM.

`PCFTEX4.DAT`, `PCFTEX.DAT`, `LGR.DAT`: varios `FORM…ILBM` concatenados (formato Deluxe
Paint; ver `codec/ilbm.py`). Contienen los LOGOS y pantallas del front-end DOS (el rótulo
"PC FUTBOL 4.0", el actualizador "HobbyTex", iconos, botones…). NO están en los datos del
manager (GFX*.DAT); viven sueltos en la raíz del juego y solo estaban en el CD original.

Editar una imagen intenta conservar el tamaño EXACTO del BODY (ByteRun1 re-comprimido +
relleno con `0x80`=NOP) → el contenedor queda byte-idéntico salvo esa imagen y los offsets
no se mueven. Si la nueva imagen no cabe comprimida, se reconstruye el contenedor entero
(los FORM se leen secuencialmente por su tamaño, sin índice externo, así que es seguro).
"""
from __future__ import annotations

from ..codec import ilbm


def list_images(data: bytes) -> list[dict]:
    """[{i, w, h}] de cada imagen ILBM del contenedor."""
    out = []
    for i, (off, size) in enumerate(ilbm.iter_forms(data)):
        info = ilbm.parse_form(data, off, size)
        out.append({"i": i, "w": info["w"], "h": info["h"]})
    return out


def image_png(data: bytes, i: int) -> bytes | None:
    forms = ilbm.iter_forms(data)
    if not (0 <= i < len(forms)):
        return None
    off, size = forms[i]
    return ilbm.decode_png(data, off, size)


def replace_image(data: bytes, i: int, png: bytes) -> bytes:
    """Devuelve el contenedor con la imagen `i` sustituida por `png` (cuantizado a su paleta
    y su geometría). Conserva longitud si cabe; si no, reconstruye."""
    forms = ilbm.iter_forms(data)
    if not (0 <= i < len(forms)):
        raise ValueError("imagen no válida")
    off, size = forms[i]
    info = ilbm.parse_form(data, off, size)
    w, h, npl, comp = info["w"], info["h"], info["nplanes"], info["comp"]
    palette = [(info["cmap"][k * 3], info["cmap"][k * 3 + 1], info["cmap"][k * 3 + 2])
               for k in range(len(info["cmap"]) // 3)] if info["cmap"] else []
    body = ilbm.encode_body(png, w, h, npl, palette, comp)
    if len(body) <= info["body_len"]:
        # in-place: encaja en el hueco → relleno con NOP (0x80), offsets intactos
        buf = bytearray(data)
        bo = info["body_off"]
        buf[bo:bo + len(body)] = body
        for k in range(bo + len(body), bo + info["body_len"]):
            buf[k] = 0x80
        return bytes(buf)
    # no cabe → reconstruir este FORM y concatenar el resto
    new_form = ilbm.build_form(w, h, npl, info["cmap"] or b"", body, comp)
    return data[:off] + new_form + data[off + size:]
