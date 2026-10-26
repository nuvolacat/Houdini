"""Acceso a los datos maestros semilla (exportados de la base de datos de un editor comunitario).

    countries.json  206 países  (pointer, name, name_de, in_pcf5, skin, hair, eu)
    teams.json     1378 equipos (pointer, name, country)
    tactics.json     15 tácticas
    kits.json        53 equipaciones (id, shirt, shorts)
    community_pointers.json  1352 equipos — numeración CANÓNICA de la comunidad
        (puntero = ID de catálogo con rangos por país; "Punteros Equipos V.2020"
        de peu7510). Superset consistente del mdb (Barcelona=1, R.Madrid=4…).
        El tramo 5781-9000 está LIBRE en esta numeración (Argentina usa 9000+).
    pcf4_camisas.json  44 equipos — de qué hueco de PC Fútbol 4.0 sale la camiseta de
        cada club (tabla escrita a mano, ver `pcf4_camisas()`).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def _load(name: str) -> list[dict]:
    path = _DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path.name} en refdata/"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def countries() -> list[dict]:
    return _load("countries")


def teams() -> list[dict]:
    return _load("teams")


def tactics() -> list[dict]:
    return _load("tactics")


def kits() -> list[dict]:
    return _load("kits")


def pcf4_tactics() -> list[dict]:
    """Las 6 formaciones con nombre de PCF 4.0 ("Táctica 4-4-2"…), extraídas de los
    equipos de la base (el juego no las guarda en claro en sus .DAT)."""
    return _load("pcf4_tactics")


def community_pointers() -> list[dict]:
    """Numeración canónica comunitaria (pointer, name, country código refdata)."""
    return _load("community_pointers")


def pcf4_camisas() -> dict:
    """tid original de PCF 4.0 -> {nombre, claves} de los 44 equipos que TIENEN camisa
    dibujada (los 22 de Primera y los 22 de Segunda del 95-96; los otros 191 de la base
    no tienen fichero en DBDAT/CAMISAS). Tabla FIJA y escrita a mano: sirve para devolverle
    a cada club su propia camiseta cuando el import lo coloca en el hueco de otro."""
    return _load("pcf4_camisas")  # type: ignore[return-value]
