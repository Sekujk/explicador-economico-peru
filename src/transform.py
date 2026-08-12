"""Transformaciones puras (sin red ni base de datos) sobre series de (fecha, valor)."""

from datetime import date


def ordenar_y_deduplicar(puntos: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """Ordena por fecha y, si hay fechas repetidas, se queda con el último valor visto."""
    por_fecha = {}
    for fecha, valor in puntos:
        por_fecha[fecha] = valor
    return sorted(por_fecha.items())


def calcular_variaciones(puntos: list[tuple[date, float]]) -> list[dict]:
    """A partir de una serie ordenada, calcula la variación % respecto al punto anterior.

    Devuelve una lista de dicts: {"fecha", "valor", "variacion_pct"}.
    El primer punto siempre tiene variacion_pct = None (no hay punto previo).
    """
    puntos_ordenados = ordenar_y_deduplicar(puntos)

    resultado = []
    valor_anterior = None
    for fecha, valor in puntos_ordenados:
        variacion_pct = None
        if valor_anterior not in (None, 0):
            variacion_pct = round((valor - valor_anterior) / valor_anterior * 100, 4)
        resultado.append({"fecha": fecha, "valor": valor, "variacion_pct": variacion_pct})
        valor_anterior = valor

    return resultado
