"""Un equipo nunca puede quedar en dos divisiones, y las divisiones no cambian de tamaño.

Un mod real de 2001 salió con 30 equipos en dos divisiones a la vez (el Huesca en 2ªB y en
Tercera) y con los grupos de Tercera a 22 cuando Dinamic los juega a 20: el juego respondía «La
aplicación no puede continuar» (foro, 14-sep-2026).
"""
import struct

from houdini_engine.formats import pcf7_manager as PM


def _binario(*tablas):
    """Bytes con las tablas seguidas; devuelve (bytes, [(offset, plazas)])."""
    b = bytearray()
    sitios = []
    for fabrica in tablas:
        sitios.append((len(b), len(fabrica)))
        b += struct.pack(f"<{len(fabrica)}H", *fabrica)
    return b, sitios


def _lee(b, off, n):
    return list(struct.unpack_from(f"<{n}H", bytes(b), off))


def test_la_plaza_libre_no_repite_un_equipo_de_otra_division():
    # fábrica: 2ªB = [10, 12]; Tercera = [20, 11]  (el 11 de fábrica estaba en Tercera)
    b, ((o1, n1), (o2, n2)) = _binario([10, 12], [20, 11])
    # el plan sube al 11 a 2ªB y a la Tercera solo le da un equipo
    PM.rellena_divisiones(b, [(o1, n1, [10, 11]), (o2, n2, [20])])
    todos = _lee(b, o1, n1) + _lee(b, o2, n2)
    assert len(set(todos)) == len(todos)                  # nadie en dos divisiones
    assert 0 not in todos                                 # y ninguna plaza a 0
    assert _lee(b, o2, n2) == [20, 12]                    # el 12, que el plan dejó sin sitio


def test_no_se_llenan_los_huecos_que_dinamic_dejo_a_cero():
    # grupo de Tercera de 2001: hueco para 4, Dinamic juega con 2
    b, ((o, n),) = _binario([5, 6, 0, 0])
    PM.rellena_divisiones(b, [(o, n, [7, 8, 9, 10])])
    assert _lee(b, o, n) == [7, 8, 0, 0]                  # el grupo sigue siendo de 2


def test_los_que_no_caben_rellenan_otra_division_incompleta():
    # Tercera I con 2 plazas vivas y un plan de 3; Tercera II con 2 plazas y plan vacío,
    # cuyos equipos de fábrica ya juegan en la I
    b, ((o1, n1), (o2, n2)) = _binario([1, 2], [1, 2])
    PM.rellena_divisiones(b, [(o1, n1, [1, 2, 3, 4]), (o2, n2, [])])
    t1, t2 = _lee(b, o1, n1), _lee(b, o2, n2)
    assert t1 == [1, 2]
    assert sorted(t2) == [3, 4]                           # los que sobraron de la I, colocados
    assert len(set(t1 + t2)) == len(t1 + t2)


def test_un_plan_completo_se_escribe_tal_cual():
    b, ((o1, n1), (o2, n2)) = _binario([1, 2, 3], [4, 5])
    PM.rellena_divisiones(b, [(o1, n1, [9, 8, 7]), (o2, n2, [6, 5])])
    assert _lee(b, o1, n1) == [9, 8, 7] and _lee(b, o2, n2) == [6, 5]


def test_sin_reserva_se_conserva_el_de_fabrica_antes_que_un_cero():
    # último recurso: no queda nadie libre → repetir antes que dejar el código 0
    b, ((o1, n1), (o2, n2)) = _binario([1], [1])
    PM.rellena_divisiones(b, [(o1, n1, [1]), (o2, n2, [])])
    assert 0 not in _lee(b, o2, n2)


def test_set_divisions_de_2001_ya_no_duplica():
    """La función de verdad, con las tablas de 2001: dos divisiones españolas incompletas."""
    from houdini_engine.formats import pcf2000_manager as P20M
    tabs = [t for t in P20M._divisions("2001") if t[0] == 22][:2]
    hasta = max(off + n * 2 for _p, _l, off, n in tabs)
    b = bytearray(hasta + 16)
    codigo = 100
    for _p, _l, off, n in tabs:                          # fábrica: todo lleno, códigos únicos
        for i in range(n):
            struct.pack_into("<H", b, off + i * 2, codigo)
            codigo += 1
    (p1, l1, off1, n1), (p2, l2, off2, n2) = tabs
    f1 = _lee(b, off1, n1)
    f2 = _lee(b, off2, n2)
    # el plan mete en la 1ª TODOS los de fábrica de la 2ª, y a la 2ª no le da ninguno
    nuevo = P20M.set_divisions(bytes(b), "2001",
                               [(p1, l1, f2[:n1]), (p2, l2, [])])
    t1, t2 = _lee(nuevo, off1, n1), _lee(nuevo, off2, n2)
    assert len(set(t1 + t2)) == len(t1 + t2)
    assert 0 not in t1 + t2


def test_la_copia_de_copa_no_pisa_otra_division():
    """Las copas nacionales repiten la lista de su liga. Buscándolas DESPUÉS de escribir, la
    Segunda nueva (que el plan había dejado igual que la Primera de fábrica) se tomaba por copia
    de la Primera y se sobrescribía."""
    # Primera, Segunda y, aparte, la copa que repite a la Primera de fábrica
    b, ((o1, n1), (o2, n2), (oc, nc)) = _binario([1, 2], [3, 4], [1, 2])
    PM.escribe_divisiones(b, [(o1, n1, [3, 4]), (o2, n2, [1, 2])])
    assert _lee(b, o1, n1) == [3, 4]
    assert _lee(b, o2, n2) == [1, 2]                     # la Segunda NO se toca por la copia
    assert _lee(b, oc, nc) == [3, 4]                     # y la copa sigue a su Primera
