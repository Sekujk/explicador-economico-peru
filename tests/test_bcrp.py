from datetime import date

from src.extract.bcrp import _parse_period_name, _rango_fechas


def test_parse_period_name_diaria():
    assert _parse_period_name("01.Jul.26", "diaria") == date(2026, 7, 1)


def test_parse_period_name_mensual():
    assert _parse_period_name("Ene.2026", "mensual") == date(2026, 1, 1)


def test_rango_fechas_diaria_usa_formato_iso():
    inicio, fin = _rango_fechas(date(2026, 7, 1), date(2026, 8, 5), "diaria")
    assert (inicio, fin) == ("2026-07-01", "2026-08-05")


def test_rango_fechas_mensual_usa_formato_anio_guion_mes_sin_ceros():
    inicio, fin = _rango_fechas(date(2026, 1, 5), date(2026, 6, 20), "mensual")
    assert (inicio, fin) == ("2026-1", "2026-6")
