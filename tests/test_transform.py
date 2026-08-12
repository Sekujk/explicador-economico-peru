from datetime import date

from src.transform import calcular_variaciones, ordenar_y_deduplicar


def test_ordenar_y_deduplicar_ordena_por_fecha():
    puntos = [(date(2026, 1, 3), 10.0), (date(2026, 1, 1), 5.0), (date(2026, 1, 2), 7.0)]
    assert ordenar_y_deduplicar(puntos) == [
        (date(2026, 1, 1), 5.0),
        (date(2026, 1, 2), 7.0),
        (date(2026, 1, 3), 10.0),
    ]


def test_ordenar_y_deduplicar_se_queda_con_el_ultimo_valor_de_fechas_repetidas():
    puntos = [(date(2026, 1, 1), 5.0), (date(2026, 1, 1), 9.0)]
    assert ordenar_y_deduplicar(puntos) == [(date(2026, 1, 1), 9.0)]


def test_calcular_variaciones_primer_punto_sin_variacion():
    puntos = [(date(2026, 1, 1), 10.0)]
    resultado = calcular_variaciones(puntos)
    assert resultado == [{"fecha": date(2026, 1, 1), "valor": 10.0, "variacion_pct": None}]


def test_calcular_variaciones_calcula_porcentaje_respecto_al_punto_anterior():
    puntos = [(date(2026, 1, 1), 10.0), (date(2026, 1, 2), 11.0)]
    resultado = calcular_variaciones(puntos)
    assert resultado[1]["variacion_pct"] == 10.0


def test_calcular_variaciones_no_divide_por_cero():
    puntos = [(date(2026, 1, 1), 0.0), (date(2026, 1, 2), 5.0)]
    resultado = calcular_variaciones(puntos)
    assert resultado[1]["variacion_pct"] is None
