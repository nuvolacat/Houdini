"""Tests del ajuste de media objetivo (jugador / equipo). Puros, sin datos del juego."""
from houdini_engine import rating as R


def test_media_of():
    assert R.media_of([88, 84, 86, 82]) == 85
    assert R.media_of([99, 99, 99, 99]) == 99
    assert R.media_of([]) == 0


def test_stats_for_target_exact():
    # sube: media exacta y reparto equilibrado dentro de [1,99]
    ns = R.stats_for_target([88, 84, 86, 82], 89)
    assert R.media_of(ns) == 89
    assert all(1 <= v <= 99 for v in ns)
    # baja
    ns = R.stats_for_target([80, 76, 78, 78], 70)
    assert R.media_of(ns) == 70
    # tope: no puede pasar de 99
    assert R.media_of(R.stats_for_target([99, 99, 99, 99], 120)) == 99


def test_team_reaches_target_and_priority():
    squad = [91, 89, 88, 86, 85, 84, 83, 82, 81, 80, 78, 77, 76, 74, 72, 70, 68, 60, 55, 48, 45]
    new = R.team_player_targets(squad, 85)
    # el promedio cae justo en el objetivo
    assert round(sum(new) / len(new)) == 85
    # todo dentro de rango
    assert all(1 <= v <= 99 for v in new)
    # nadie BAJA al subir el equipo
    assert all(b >= a for a, b in zip(squad, new))
    # prioridad leve a los de más media: un jugador alto (no topado) sube al menos tanto
    # como uno bajo. Comparamos el 80 (margen de sobra) con el 55.
    d = {a: b - a for a, b in zip(squad, new)}
    assert d[80] >= d[55]
    # "sin pasarse": el de 55 no salta a 80
    assert dict(zip(squad, new))[55] < 80


def test_team_lower():
    squad = [90, 88, 85, 84, 82, 80, 78, 75, 70, 60]
    new = R.team_player_targets(squad, 70)
    assert round(sum(new) / len(new)) == 70
    assert all(b <= a for a, b in zip(squad, new))   # nadie sube al bajar


def test_team_empty():
    assert R.team_player_targets([], 90) == []
