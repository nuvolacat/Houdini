"""Emparejado de equipos del PKF con los punteros canónicos de Dinamic.

El puntero de equipo que usan escudos (``eqVVPPPP.bmp``), fotos por carpeta y
ficheros DBC (``EQVVPPPP.DBC``) es el de la lista maestra de Dinamic
(``refdata/teams.json``, tabla PuntersEquips de pcf.mdb). Ese puntero NO está
guardado en el bloque de equipo del PKF (el juego lo resuelve por posición en
las tablas de competición de manager.exe), así que lo recuperamos emparejando
por nombre + país. Verificado contra los contenedores de escudos originales:
Barcelona=1, R. Madrid=4, At. Madrid=12, etc.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from houdini_engine import refdata

_STOP = {"fc", "cf", "rc", "cd", "ud", "sd", "ad", "club", "de", "the",
         "ac", "as", "us", "ss", "calcio"}
_MIN_SCORE = 0.72


def _fold(s: str) -> list[str]:
    # ø ł đ ı æ ß þ ð no los descompone NFD: sin esto se vuelven separador y parten el nombre
    # («Brøndby» → «br», «ndby»). Ver `codec.text.pliega_letras`.
    from .codec.text import pliega_letras
    s = "".join(c for c in unicodedata.normalize("NFD", pliega_letras(s).lower())
                if unicodedata.category(c) != "Mn")
    # siglas de club con punto ("C.F.", "F.C.", "S.A.D.") fuera ANTES de
    # tokenizar: si no, la C suelta confunde con el filial C ("R. Madrid C").
    # Solo grupos de 2+ letras con punto: "R. Madrid" (abreviatura real) se queda.
    # Y la inicial suelta del principio cuando la sigue OTRA abreviatura con punto
    # ("C. At. Madrid" → "At. Madrid"): esa 'c' huérfana era un COMODÍN, porque en la
    # comparación una letra suelta casa con cualquier palabra que empiece igual. Por eso
    # el filial del Atlético salía con el escudo del Celta y el primer equipo casaba con
    # Cartagena. "R. Madrid" no se toca: ahí la inicial NO va seguida de otra abreviatura.
    s = re.sub(r"^\s*[a-z]\.\s*(?=[a-z]{2,}\.)", " ", s)
    s = re.sub(r"\b(?:[a-z]\.\s*){2,}", " ", s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in _STOP]


def _suffix(tokens: list[str]) -> str:
    """Letra de filial al final del nombre ('b'/'c'), si la hay."""
    return tokens[-1] if tokens and tokens[-1] in ("b", "c") else ""


def _abbrev(short: list[str], long_: list[str]) -> bool:
    """'R. Madrid' ~ 'Real Madrid', 'Man Utd' ~ 'Manchester U.': cada token del
    nombre corto casa (prefijo en cualquier dirección) con uno del largo, en orden."""
    it = iter(long_)
    return all(any(l.startswith(s) or s.startswith(l) for l in it) for s in short)


def _score(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = " ".join(a), " ".join(b)
    if sa == sb:
        return 1.0
    if _abbrev(a, b) or _abbrev(b, a):
        s = 0.93
    else:
        s = SequenceMatcher(None, sa, sb).ratio()
    # guardia de filial: el club y su B/C solo casan entre sí
    if _suffix(a) != _suffix(b):
        s *= 0.6
    return s


def match_team_pointers(teams, prefer: set[int] | None = None) -> dict[int, int]:
    """índice de equipo -> puntero canónico. Asignación única por puntero.

    ``teams``: iterable con .short_name, .long_name, .country.
    ``prefer``: punteros con imagen disponible (desempatan, +0.02).
    """
    prefer = prefer or set()
    cands = [(t["pointer"], _fold(t["name"]), t["country"]) for t in refdata.teams()]
    scored: list[tuple[float, int, int]] = []
    for i, t in enumerate(teams):
        tk_s, tk_l = _fold(t.short_name), _fold(t.long_name)
        for ptr, mtk, mc in cands:
            if mc != t.country:
                continue
            s = max(_score(tk_s, mtk), _score(tk_l, mtk))
            if s >= _MIN_SCORE:
                scored.append((s + (0.02 if ptr in prefer else 0.0), i, ptr))
    result: dict[int, int] = {}
    used: set[int] = set()
    # a igualdad de puntuación gana el puntero MÁS BAJO (los principales van
    # primero en la lista maestra: R. Madrid=4 antes que R. Madrid C=98)
    for s, i, ptr in sorted(scored, key=lambda x: (-x[0], x[2], x[1])):
        if i in result or ptr in used:
            continue
        result[i] = ptr
        used.add(ptr)
    return result
