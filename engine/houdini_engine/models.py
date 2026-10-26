"""Modelos de dominio de PCF 5/6.

Basados en el volcado de pcf.mdb (tablas Jugadors, Equips, Tactiques...).
Las medias siguen el orden VE RE AG CA RG RM PA TI EN PO (v5); en v6 se
intercambian RG<->RM al leer/escribir (lo gestiona el codec de formato).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class GameVersion(IntEnum):
    PCF5 = 5
    PCF6 = 6


class Skin(IntEnum):
    """Tono de piel del avatar que dibuja el juego (valores del formato original)."""
    TONE_1 = 1
    TONE_2 = 2
    TONE_3 = 3


class Hair(IntEnum):
    BLOND = 1
    BALD = 2
    DARK = 3
    WHITE = 4
    RED = 5
    BROWN = 6


class PlayerType(IntEnum):
    GOALKEEPER = 0
    DEFENDER = 1
    MIDFIELDER = 2
    FORWARD = 3


# Demarcaciones (0x00 vacío .. 0x12). 
DEMARCACIONES = {
    0x00: "Vacío", 0x01: "Portero", 0x02: "Lateral derecho", 0x03: "Lateral izquierdo",
    0x04: "Libre", 0x05: "Central izquierdo", 0x06: "Central derecho",
    0x07: "Centrocampista derecha", 0x08: "Interior derecho", 0x09: "Delantero centro",
    0x0A: "Medio centro organizador", 0x0B: "Centrocampista izquierda",
    0x0C: "Extremo derecho", 0x0D: "Media punta por el centro", 0x0E: "Extremo izquierdo",
    0x0F: "Medio centro defensivo", 0x10: "Media punta derecha",
    0x11: "Media punta izquierda", 0x12: "Interior izquierdo",
}


@dataclass
class Ratings:
    """Medias del jugador (0..99)."""
    ve: int = 0  # velocidad
    re: int = 0  # resistencia
    ag: int = 0  # agresividad
    ca: int = 0  # calidad
    rg: int = 0  # regate
    rm: int = 0  # remate
    pa: int = 0  # pase
    ti: int = 0  # tiro
    en: int = 0  # entradas
    po: int = 0  # portero


@dataclass
class Player:
    pointer: int
    short_name: str
    long_name: str
    number: int = 0                 # dorsal
    lineup_position: int = 0        # 1-11 titular, 12-16 suplente, 17-98 no conv., 99 desactivado
    origin: int = 0                 # 0 continúa, 1 fichaje, 2 asciende, 3 baja
    demarcations: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])
    country: int = 0
    skin: int = Skin.TONE_1
    hair: int = Hair.DARK
    ptype: int = PlayerType.MIDFIELDER
    birth_day: int = 0
    birth_month: int = 0
    birth_year: int = 0
    height: int = 0                 # cm
    weight: int = 0                 # kg
    comments: str = ""
    ratings: Ratings = field(default_factory=Ratings)


@dataclass
class Team:
    pointer: int
    name: str
    stadium: str = ""
    country: int = 0
    capacity: int = 0               # aforo
    members: int = 0                # socios
    budget: int = 0                 # presupuesto
    coach: str = ""
    players: list[Player] = field(default_factory=list)
    raw_block_len: int | None = None  # longitud fija original del bloque (invariante al escribir)


@dataclass
class Database:
    version: GameVersion
    teams: list[Team] = field(default_factory=list)
