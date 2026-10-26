"""PCF 3.0 — reglas cableadas en el manager (`PCMANAG.DAT`), 2026-08-30.

`PCMANAG.DAT` es el ejecutable del modo Liga: un MZ de DOS de 16 bits compilado con Borland C++
1991. Igual que el `manager.exe` de 5.0/6.0, lleva topes escritos en el propio código.

**TOPE DE EXTRANJEROS TITULARES.** El juego avisa con «El máximo de jugadores extranjeros
titulares es 3». La comprobación se desensambló y es esta, en DOS sitios (dos pantallas):

    push  word ptr [bp-8]      ; el equipo
    lcall <rutina>             ; cuenta cuántos extranjeros hay en el once
    pop   cx
    mov   word ptr [bp-4], ax
    cmp   ax, 3                ; ← el tope
    jbe   ok                   ; si no pasa de 3, adelante
    ...                        ; si no, saca el aviso

Se localiza por ESA FORMA, no por offset fijo: un `cmp ax, imm16` seguido de `jbe` justo detrás
de una llamada que devuelve el recuento. Así vale para cualquier build que compartan estos
ficheros y no se rompe si el ejecutable cambia de sitio.

**Por qué no se encontraba antes:** buscándolo por patrones de bytes se calculó mal la longitud
de `cmp ax, imm16` (3 bytes, no 4) y el `jbe` quedaba fuera de la ventana. El fichero siempre lo
tuvo.
"""
from __future__ import annotations

import re

# lcall(5) · pop cx(1) · mov [bp-N],ax(3) · cmp ax,imm16(3) · jbe(1)
_CUPO = re.compile(rb"\x9a....\x59\x89\x46.\x3d(.)\x00\x76", re.DOTALL)
_OFF_IMM = 10          # dónde cae el inmediato dentro de la coincidencia
_OFF_JBE = 12          # dónde cae el `jbe`

TOPE_MAX = 11          # once titulares: más que eso no tiene sentido


def sitios_extranjeros(data: bytes) -> list[int]:
    """Offsets del byte que guarda el tope (uno por cada sitio donde el juego lo comprueba)."""
    return [m.start() + _OFF_IMM for m in _CUPO.finditer(data)]


def limite_extranjeros(data: bytes) -> int | None:
    """El tope que hay puesto, o None si no se localiza. Si los sitios no coinciden, manda el
    primero (no debería pasar: el juego los escribe iguales)."""
    s = sitios_extranjeros(data)
    return data[s[0]] if s else None


def set_limite_extranjeros(data: bytes, tope: int) -> bytes:
    """Cambia el tope en TODOS los sitios. `tope` entre 0 y 11."""
    sitios = sitios_extranjeros(data)
    if not sitios:
        raise ValueError("no se localiza el tope de extranjeros en este ejecutable")
    if not 0 <= tope <= TOPE_MAX:
        raise ValueError(f"el tope va de 0 a {TOPE_MAX}")
    b = bytearray(data)
    for off in sitios:
        b[off] = tope
    return bytes(b)


LIMITS = [{"key": "extranjeros_alinear", "label": "Extranjeros en el once",
           "help": "Cuántos jugadores de fuera puedes alinear a la vez. El juego avisa: «El "
                   "máximo de jugadores extranjeros titulares es 3». La regla real de la "
                   "temporada 94-95 eran 3; súbelo si quieres plantillas sin ese tope.",
           "factory": 3, "min": 0, "max": TOPE_MAX}]


def limits_read(data: bytes) -> "list[dict] | None":
    """Topes del motor con la forma que espera la pantalla (la misma que en v5/6)."""
    v = limite_extranjeros(data)
    if v is None:
        return None
    return [{**LIMITS[0], "value": v}]


def limits_write(data: bytes, valores: dict) -> bytes:
    """Aplica los topes que traiga `valores` (solo se conoce uno)."""
    if "extranjeros_alinear" not in valores:
        return data
    return set_limite_extranjeros(data, int(valores["extranjeros_alinear"]))


def resumen(data: bytes) -> dict:
    sitios = sitios_extranjeros(data)
    return {"disponible": bool(sitios), "extranjeros": limite_extranjeros(data),
            "sitios": len(sitios), "maximo": TOPE_MAX}
