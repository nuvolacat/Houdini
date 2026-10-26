"""Rellenar las plazas que un plan no llena NUNCA puede repetir un equipo.

El caso real: Ligue 2 de PCF7 tiene 20 plazas y la actualización solo colocó 18. Las dos
libres se rellenaban con el equipo de FÁBRICA de esa plaza… y uno de ellos ya estaba puesto
en otra plaza de la misma tabla. Resultado: un club jugando contra sí mismo y el juego
cayéndose al crear la partida (mod de un usuario, 12-sep-2026).
"""
import struct

from houdini_engine.formats.pcf7_manager import rellena_tabla


def _tabla(fabrica):
    return bytearray(struct.pack(f"<{len(fabrica)}H", *fabrica))


def _leer(b, n):
    return list(struct.unpack_from(f"<{n}H", bytes(b)))


def test_el_de_fabrica_que_ya_juega_no_se_repite():
    # plaza 20 de fábrica = 516, y el plan ya coloca al 516 en la plaza 7
    fabrica = [533, 528, 519, 514, 541, 522, 530, 523, 540, 547,
               526, 529, 539, 511, 527, 512, 524, 518, 536, 516]
    plan = [501, 508, 509, 510, 511, 512, 516, 517, 521, 522,
            524, 525, 526, 527, 530, 531, 532, 533]          # 18 para 20 plazas
    b = _tabla(fabrica)
    rellena_tabla(b, 0, 20, plan)
    salida = _leer(b, 20)
    assert len(set(salida)) == 20, f"hay repetidos: {salida}"
    assert 0 not in salida, "ninguna plaza puede quedar a 0"
    assert salida[:18] == plan, "el plan manda en sus plazas"


def test_si_el_de_fabrica_sirve_se_respeta():
    fabrica = [10, 11, 12, 13]
    plan = [20, 21]
    b = _tabla(fabrica)
    rellena_tabla(b, 0, 4, plan)
    assert _leer(b, 4) == [20, 21, 12, 13]


def test_plan_completo_no_toca_nada_mas():
    fabrica = [10, 11, 12, 13]
    plan = [20, 21, 22, 23]
    b = _tabla(fabrica)
    rellena_tabla(b, 0, 4, plan)
    assert _leer(b, 4) == plan


def test_sin_reserva_prefiere_repetir_antes_que_dejar_un_cero():
    # todos los de fábrica ya juegan: no hay recambio posible
    fabrica = [10, 11]
    plan = [10]
    b = _tabla(fabrica)
    rellena_tabla(b, 0, 2, plan)
    salida = _leer(b, 2)
    assert 0 not in salida, "un 0 cuelga el juego: es la única cosa que no vale"


def test_no_escribe_fuera_de_su_tabla():
    b = bytearray(struct.pack("<6H", 1, 2, 3, 4, 99, 99))
    rellena_tabla(b, 0, 4, [7])
    assert _leer(b, 6)[4:] == [99, 99], "ha pisado lo que hay detrás de la tabla"
