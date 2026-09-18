from datetime import date

from src.analysis import (
    calcular_correlacion,
    detectar_anomalia,
    forecast_siguiente_valor,
)


def test_calcular_correlacion_series_identicas_da_correlacion_perfecta():
    serie_a = [(date(2026, 1, i), float(i)) for i in range(1, 6)]
    serie_b = [(date(2026, 1, i), float(i) * 2) for i in range(1, 6)]

    assert calcular_correlacion(serie_a, serie_b) == 1.0


def test_calcular_correlacion_series_inversas_da_correlacion_negativa():
    serie_a = [(date(2026, 1, i), float(i)) for i in range(1, 6)]
    serie_b = [(date(2026, 1, i), -float(i)) for i in range(1, 6)]

    assert calcular_correlacion(serie_a, serie_b) == -1.0


def test_calcular_correlacion_sin_fechas_en_comun_devuelve_none():
    serie_a = [(date(2026, 1, 1), 1.0), (date(2026, 1, 2), 2.0)]
    serie_b = [(date(2026, 2, 1), 1.0), (date(2026, 2, 2), 2.0)]

    assert calcular_correlacion(serie_a, serie_b) is None


def test_forecast_siguiente_valor_tendencia_constante():
    # sube exactamente 1 por día -> el siguiente valor predicho debería ser 6.0
    puntos = [(date(2026, 1, i), float(i)) for i in range(1, 6)]

    valor_predicho, pendiente = forecast_siguiente_valor(puntos)

    assert round(valor_predicho, 4) == 6.0
    assert pendiente == 1.0


def test_forecast_siguiente_valor_insuficientes_puntos_devuelve_none():
    assert forecast_siguiente_valor([(date(2026, 1, 1), 1.0)]) is None


def test_detectar_anomalia_valor_dentro_de_rango_normal():
    puntos = [(date(2026, 1, i), 10.0) for i in range(1, 10)] + [(date(2026, 1, 10), 10.1)]

    resultado = detectar_anomalia(puntos)

    assert resultado["es_anomalia"] is False


def test_detectar_anomalia_valor_muy_alejado_se_marca():
    # historico con algo de variacion real (no constante) para que el z-score tenga sentido
    valores_historicos = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 10.3, 9.7, 10.1]
    puntos = [(date(2026, 1, i + 1), v) for i, v in enumerate(valores_historicos)]
    puntos.append((date(2026, 1, 10), 1000.0))

    resultado = detectar_anomalia(puntos)

    assert resultado["es_anomalia"] is True
    assert resultado["z_score"] > 2.0


def test_detectar_anomalia_historico_constante_no_es_evaluable():
    # ej. una tasa de referencia fija varios meses: sin varianza, el z-score
    # no está definido, así que se reporta como no evaluable (no como True/False forzado)
    puntos = [(date(2026, 1, i), 4.25) for i in range(1, 10)] + [(date(2026, 1, 10), 4.5)]

    resultado = detectar_anomalia(puntos)

    assert resultado["es_anomalia"] is False
    assert resultado["z_score"] is None


def test_detectar_anomalia_pocos_puntos_no_evalua():
    resultado = detectar_anomalia([(date(2026, 1, 1), 1.0), (date(2026, 1, 2), 2.0)])

    assert resultado["es_anomalia"] is False
    assert resultado["z_score"] is None
