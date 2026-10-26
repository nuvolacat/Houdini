"""Arrastrar los atributos secundarios al fijar la media (foro, 2026-08-30).

La media ES (VE+RE+AG+CA)/4, así que solo esas cuatro hacen falta para alcanzarla; el resto se
quedaba igual y dejaba incoherencias —un portero con media 90 y su atributo de portero en 20—.
Esto comprueba el reparto POR PUESTO: a cada uno le sigue lo suyo.
"""
from houdini_engine import rating as R

V56 = {"VE": 60, "RE": 60, "AG": 60, "CA": 60,
       "RG": 40, "RM": 40, "PA": 40, "TI": 40, "EN": 40, "PO": 40}


def test_al_portero_le_sube_el_portero_y_poco_mas():
    d = R.secundarias_por_media(V56, 20, 0)
    assert d["PO"] == 60                      # peso 1: sube lo mismo que la media
    assert all(d[k] == 44 for k in ("RG", "RM", "PA", "TI", "EN"))   # peso 0,2


def test_cada_puesto_tira_de_lo_suyo():
    defensa = R.secundarias_por_media(V56, 20, 1)
    medio = R.secundarias_por_media(V56, 20, 2)
    delantero = R.secundarias_por_media(V56, 20, 3)
    assert defensa["EN"] > defensa["PA"] > defensa["RG"]
    assert medio["PA"] > medio["TI"] and medio["RG"] > medio["RM"]
    assert delantero["RM"] > delantero["PA"] and delantero["TI"] > delantero["EN"]
    # a nadie que no sea portero le sube el atributo de portero
    for d in (defensa, medio, delantero):
        assert "PO" not in d


def test_baja_igual_que_sube():
    alto = dict(V56, PO=80)
    assert R.secundarias_por_media(alto, -20, 0)["PO"] == 60


def test_no_toca_lo_que_no_depende_de_lo_bueno_que_sea():
    """Penaltis, córners y faltas son especialidades, no calidad: se quedan como estén."""
    fdi = {"regate": 50, "pase": 50, "penaltis": 90, "corner_izq": 80, "falta_der": 70}
    d = R.secundarias_por_media(fdi, 20, 2)
    assert set(d) == {"regate", "pase"}


def test_sin_cambio_de_media_no_toca_nada():
    assert R.secundarias_por_media(V56, 0, 0) == {}


def test_respeta_el_tope_de_99_y_el_suelo_de_1():
    assert R.secundarias_por_media(dict(V56, PO=95), 30, 0)["PO"] == 99
    assert R.secundarias_por_media(dict(V56, PO=5), -30, 0)["PO"] == 1
