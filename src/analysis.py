"""Análisis estadístico sobre series de (fecha, valor): correlación, forecast simple
y detección de anomalías. Funciones puras, sin red ni base de datos.
"""

import statistics
from datetime import date


def alinear_por_fecha(
    serie_a: list[tuple[date, float]], serie_b: list[tuple[date, float]]
) -> tuple[list[float], list[float]]:
    """Devuelve dos listas paralelas con los valores de cada serie en las fechas
    que ambas comparten (para poder comparar series de distinta longitud/rango).
    """
    dict_a = dict(serie_a)
    dict_b = dict(serie_b)
    fechas_comunes = sorted(set(dict_a) & set(dict_b))
    return [dict_a[f] for f in fechas_comunes], [dict_b[f] for f in fechas_comunes]


def calcular_correlacion(
    serie_a: list[tuple[date, float]], serie_b: list[tuple[date, float]]
) -> float | None:
    """Correlación de Pearson entre dos series, alineadas por fecha.

    Devuelve None si no hay al menos 2 fechas en común (no se puede calcular).
    """
    valores_a, valores_b = alinear_por_fecha(serie_a, serie_b)
    if len(valores_a) < 2 or len(set(valores_a)) < 2 or len(set(valores_b)) < 2:
        return None
    return statistics.correlation(valores_a, valores_b)


def forecast_siguiente_valor(puntos: list[tuple[date, float]]) -> tuple[float, float] | None:
    """Regresión lineal simple sobre toda la serie; predice el siguiente valor.

    Devuelve (valor_predicho, pendiente), o None si no hay suficientes puntos.
    La "pendiente" indica la tendencia: positiva = subiendo, negativa = bajando.
    """
    puntos_ordenados = sorted(puntos)
    if len(puntos_ordenados) < 2:
        return None

    xs = list(range(len(puntos_ordenados)))
    ys = [valor for _, valor in puntos_ordenados]
    pendiente, intercepto = statistics.linear_regression(xs, ys)

    x_siguiente = len(puntos_ordenados)
    valor_predicho = pendiente * x_siguiente + intercepto
    return valor_predicho, pendiente


def detectar_anomalia(puntos: list[tuple[date, float]], umbral_desviaciones: float = 2.0) -> dict:
    """Compara el último valor contra la media/desviación estándar del resto de la serie.

    Si el último valor está a más de `umbral_desviaciones` desviaciones estándar
    de la media histórica, se marca como anomalía.
    """
    puntos_ordenados = sorted(puntos)
    valores = [valor for _, valor in puntos_ordenados]

    if len(valores) < 3:
        return {"es_anomalia": False, "z_score": None}

    historicos, ultimo = valores[:-1], valores[-1]
    media = statistics.mean(historicos)
    desviacion = statistics.stdev(historicos)

    if desviacion == 0:
        # El histórico no varió nada (ej. una tasa que estuvo fija varios meses):
        # el z-score no está definido (división por cero). No se puede afirmar
        # de forma estadísticamente honesta si el valor nuevo es "anómalo" o no
        # con una muestra sin varianza — se reporta como no evaluable, no como False.
        return {"es_anomalia": False, "z_score": None}

    z_score = (ultimo - media) / desviacion
    return {"es_anomalia": abs(z_score) >= umbral_desviaciones, "z_score": round(z_score, 4)}
