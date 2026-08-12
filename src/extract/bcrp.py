"""Cliente para la API pública de series estadísticas del BCRP.

Formato real verificado (2026-08-06) contra
https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api :

    https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigo}/json/{inicio}/{fin}/esp

- Series diarias: {inicio}/{fin} en formato YYYY-MM-DD, y cada "period.name"
  viene como "DD.Mmm.YY" (ej. "01.Jul.26").
- Series mensuales: {inicio}/{fin} en formato YYYY-M, y cada "period.name"
  viene como "Mmm.YYYY" (ej. "Ene.2026").
- Valores faltantes vienen como el string "n.d." (se descartan).
"""

from datetime import date

import requests

_BASE_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"

_MESES = {
    "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12,
}


def _parse_period_name(name: str, frecuencia: str) -> date:
    if frecuencia == "diaria":
        dia, mes_abbr, anio_corto = name.split(".")
        return date(2000 + int(anio_corto), _MESES[mes_abbr], int(dia))
    if frecuencia == "mensual":
        mes_abbr, anio = name.split(".")
        return date(int(anio), _MESES[mes_abbr], 1)
    raise ValueError(f"Frecuencia no soportada: {frecuencia}")


def _rango_fechas(fecha_inicio: date, fecha_fin: date, frecuencia: str) -> tuple[str, str]:
    if frecuencia == "diaria":
        return fecha_inicio.isoformat(), fecha_fin.isoformat()
    if frecuencia == "mensual":
        return f"{fecha_inicio.year}-{fecha_inicio.month}", f"{fecha_fin.year}-{fecha_fin.month}"
    raise ValueError(f"Frecuencia no soportada: {frecuencia}")


def fetch_series(codigo: str, frecuencia: str, fecha_inicio: date, fecha_fin: date) -> list[tuple[date, float]]:
    """Descarga una serie del BCRP y la devuelve como lista de (fecha, valor).

    Los puntos con valor "n.d." (dato faltante) se omiten.
    """
    inicio_str, fin_str = _rango_fechas(fecha_inicio, fecha_fin, frecuencia)
    url = f"{_BASE_URL}/{codigo}/json/{inicio_str}/{fin_str}/esp"

    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()
    data = respuesta.json()

    puntos = []
    for periodo in data.get("periods", []):
        valor_raw = periodo["values"][0]
        if valor_raw == "n.d.":
            continue
        fecha = _parse_period_name(periodo["name"], frecuencia)
        puntos.append((fecha, float(valor_raw)))

    return puntos
