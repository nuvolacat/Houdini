"""Táctica dibujada: mover un jugador sin romper el bloque.

Se trabaja sobre las 15 formaciones estándar del `pcf.mdb`, que son datos reales del
juego, así que el test corre sin necesidad del material gordo (los .PKF gitignorados).
"""
import struct

import pytest

from houdini_engine import tactics as T


def _formaciones():
    from houdini_engine import refdata
    out = []
    for t in refdata.tactics():
        b = bytes.fromhex(t.get("Hex") or "")
        if len(b) == T.BLOCK_LEN - 2:      # el mdb guarda los 174 sin el u16 de cabecera
            out.append((t["Nom"], b"\x00\x00" + b))
    return out


@pytest.fixture(scope="module")
def formaciones():
    f = _formaciones()
    if not f:
        pytest.skip("sin refdata de tácticas")
    return f


def _campos(blob, j):
    return struct.unpack_from("<8H", blob, j * 16)


def test_invariante_de_partida(formaciones):
    """La zona contiene las dos posiciones en las 15 formaciones (330 casos)."""
    for _nom, blob in formaciones:
        for j in range(T.PLAYERS):
            w = _campos(blob, j)
            assert w[0] <= w[4] <= w[0] + w[2] and w[0] <= w[6] <= w[0] + w[2]
            assert w[1] <= w[5] <= w[1] + w[3] and w[1] <= w[7] <= w[1] + w[3]


def test_mueve_solo_al_jugador_pedido(formaciones):
    _nom, blob = formaciones[0]
    out = T.shift_player(blob, 5, 0.7 * T.X_MAX, 0.3 * T.Y_MAX)
    assert len(out) == T.BLOCK_LEN
    for j in range(T.PLAYERS):
        if j != 5:
            assert _campos(out, j) == _campos(blob, j), f"jugador {j} tocado"
    assert _campos(out, 5) != _campos(blob, 5)


def test_conserva_invariantes_y_campo(formaciones):
    """Se mueva a donde se mueva, la zona sigue dentro del campo y sigue conteniendo
    las dos posiciones."""
    destinos = [(0.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.99, 0.02), (0.02, 0.99)]
    for _nom, blob in formaciones:
        for j in (0, 3, 7, 10):
            for which in ("nat", "def", "atk"):
                for gx, gy in destinos:
                    out = T.shift_player(blob, j, gx * T.X_MAX, gy * T.Y_MAX, which=which)
                    w = _campos(out, j)
                    assert 0 <= w[0] and w[0] + w[2] <= T.X_MAX
                    assert 0 <= w[1] and w[1] + w[3] <= T.Y_MAX
                    assert w[0] <= w[4] <= w[0] + w[2] and w[0] <= w[6] <= w[0] + w[2]
                    assert w[1] <= w[5] <= w[1] + w[3] and w[1] <= w[7] <= w[1] + w[3]
                    assert all(0 <= v <= 0xFFFF for v in w)


def test_llega_al_destino(formaciones):
    """Colocando UNA posición se llega al punto pedido (±1 por el redondeo a entero).

    El modo `nat` no siempre puede: su punto es la media de repliegue y ataque, así que
    acercarlo a la línea de gol sacaría del campo la posición de ataque. Por eso el editor
    ofrece los tres modos."""
    _nom, blob = formaciones[0]
    for j in (3, 7, 10):
        for which, campos in (("def", (4, 5)), ("atk", (6, 7))):
            out = T.shift_player(blob, j, 0.75 * T.X_MAX, 0.25 * T.Y_MAX, which=which)
            w = _campos(out, j)
            assert abs(w[campos[0]] - 0.75 * T.X_MAX) <= 1
            assert abs(w[campos[1]] - 0.25 * T.Y_MAX) <= 1


def test_portero_no_se_mueve_a_lo_largo(formaciones):
    """En v5/6 el primer u16 (zona xMin del portero) NO se guarda en el fichero: solo van
    174 de los 176 B. Si el portero pudiera avanzar, ese campo se perdería al escribir."""
    for _nom, blob in formaciones:
        out = T.shift_player(blob, 0, 0.9 * T.X_MAX, 0.9 * T.Y_MAX, keep_x0=True)
        assert struct.unpack_from("<H", out, 0)[0] == 0
        assert _campos(out, 0)[4] == _campos(blob, 0)[4]     # x de repliegue intacta
        assert _campos(out, 0)[5] != _campos(blob, 0)[5]     # pero a lo ancho sí se mueve


def test_sin_keep_x0_el_portero_avanza(formaciones):
    """PCF4 guarda los 176 B completos, así que allí el portero sí puede adelantarse."""
    _nom, blob = formaciones[0]
    out = T.shift_player(blob, 0, 0.4 * T.X_MAX, 0.5 * T.Y_MAX, keep_x0=False)
    assert _campos(out, 0)[4] > _campos(blob, 0)[4]


def test_blob_corto_o_jugador_invalido_no_revienta(formaciones):
    _nom, blob = formaciones[0]
    assert T.shift_player(b"", 0, 10, 10) == b""
    assert T.shift_player(blob[:100], 0, 10, 10) == blob[:100]
    assert T.shift_player(blob, 11, 10, 10) == blob
    assert T.shift_player(blob, -1, 10, 10) == blob
