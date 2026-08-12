"""Corre el pipeline completo: extract -> transform -> load -> resumen.

Orquestado con Prefect: cada indicador se extrae y carga como una tarea
independiente con reintentos automáticos (las APIs externas pueden fallar
de forma transitoria), dentro de un flow que se puede correr una vez
(`python -m src.main`) o programar (ver README, sección "Scheduling").
"""

from datetime import date, timedelta

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE

from src.analysis import calcular_correlacion, detectar_anomalia, forecast_siguiente_valor
from src.config import INDICADORES, Indicador
from src.db import get_engine, init_schema
from src.extract import bcrp, commodities
from src.load import cargar_indicador
from src.transform import calcular_variaciones, ordenar_y_deduplicar

_LOOKBACK_DIAS = {"diaria": 180, "mensual": 730}

# Correlación entre el tipo de cambio y el precio del cobre: Perú es un exportador
# grande de cobre, así que hay una relación económica real (no arbitraria) para
# calcular acá. Ambos son series diarias, se pueden alinear por fecha directamente.
_PAR_CORRELACION = ("tipo_cambio_venta", "precio_cobre")


def _rango_para(frecuencia: str) -> tuple[date, date]:
    hoy = date.today()
    return hoy - timedelta(days=_LOOKBACK_DIAS[frecuencia]), hoy


def _resumen(nombre: str, unidad: str, puntos_con_variacion: list[dict]) -> str:
    if not puntos_con_variacion:
        return f"{nombre}: sin datos en el rango consultado."

    ultimo = puntos_con_variacion[-1]
    if ultimo["variacion_pct"] is None:
        return f"{nombre}: {ultimo['valor']} {unidad} ({ultimo['fecha']})."

    direccion = "subió" if ultimo["variacion_pct"] >= 0 else "bajó"
    return (
        f"{nombre}: {ultimo['valor']} {unidad} ({ultimo['fecha']}), "
        f"{direccion} {abs(ultimo['variacion_pct'])}% respecto al dato anterior."
    )


def _interpretar_correlacion(r: float) -> str:
    fuerza = "fuerte" if abs(r) >= 0.7 else "moderada" if abs(r) >= 0.3 else "débil"
    direccion = "directa" if r >= 0 else "inversa"
    return f"relación {direccion} {fuerza}"


def _linea_analisis(nombre: str, unidad: str, puntos: list[tuple[date, float]]) -> str:
    forecast = forecast_siguiente_valor(puntos)
    anomalia = detectar_anomalia(puntos)

    if forecast is None:
        return f"{nombre}: datos insuficientes para forecast."

    valor_predicho, pendiente = forecast
    tendencia = "subiendo" if pendiente > 0 else "bajando" if pendiente < 0 else "estable"

    aviso_anomalia = ""
    if anomalia["z_score"] is not None and anomalia["es_anomalia"]:
        aviso_anomalia = f" [AVISO] posible anomalía (z-score {anomalia['z_score']})."

    return (
        f"{nombre}: próximo valor estimado {round(valor_predicho, 4)} {unidad} "
        f"(tendencia: {tendencia}).{aviso_anomalia}"
    )


@task(name="extraer", retries=3, retry_delay_seconds=30, log_prints=True)
def extraer(indicador: Indicador) -> list[tuple[date, float]]:
    fecha_inicio, fecha_fin = _rango_para(indicador.frecuencia)

    if indicador.fuente == "BCRP":
        puntos = bcrp.fetch_series(indicador.codigo_fuente, indicador.frecuencia, fecha_inicio, fecha_fin)
    elif indicador.fuente == "yfinance":
        puntos = commodities.fetch_series(indicador.codigo_fuente, fecha_inicio, fecha_fin)
    else:
        raise ValueError(f"Fuente no soportada: {indicador.fuente}")

    print(f"[{indicador.codigo_interno}] {len(puntos)} puntos extraídos de {indicador.fuente}.")
    return ordenar_y_deduplicar(puntos)


@task(name="cargar", retries=2, retry_delay_seconds=10, cache_policy=NO_CACHE)
def cargar(engine, indicador: Indicador, puntos: list[tuple[date, float]]) -> int:
    return cargar_indicador(engine, indicador, puntos)


@task(name="analizar")
def analizar(indicadores_con_puntos: dict[str, tuple[Indicador, list[tuple[date, float]]]]) -> list[str]:
    lineas = [
        _linea_analisis(indicador.nombre, indicador.unidad, puntos)
        for indicador, puntos in indicadores_con_puntos.values()
    ]

    codigo_a, codigo_b = _PAR_CORRELACION
    if codigo_a in indicadores_con_puntos and codigo_b in indicadores_con_puntos:
        _, puntos_a = indicadores_con_puntos[codigo_a]
        _, puntos_b = indicadores_con_puntos[codigo_b]
        r = calcular_correlacion(puntos_a, puntos_b)
        if r is not None:
            nombre_a = indicadores_con_puntos[codigo_a][0].nombre
            nombre_b = indicadores_con_puntos[codigo_b][0].nombre
            lineas.append(f"Correlación {nombre_a} vs. {nombre_b}: {round(r, 4)} ({_interpretar_correlacion(r)}).")

    return lineas


@flow(name="explicador-economico-pipeline", log_prints=True)
def run() -> None:
    logger = get_run_logger()
    engine = get_engine()
    init_schema(engine)

    resumenes = []
    indicadores_con_puntos = {}
    for indicador in INDICADORES:
        puntos = extraer(indicador)
        cantidad_cargada = cargar(engine, indicador, puntos)
        indicadores_con_puntos[indicador.codigo_interno] = (indicador, puntos)

        con_variacion = calcular_variaciones(puntos)
        resumenes.append(_resumen(indicador.nombre, indicador.unidad, con_variacion))

        logger.info(f"[{indicador.codigo_interno}] {cantidad_cargada} puntos cargados.")

    print("\n--- Resumen del día ---")
    for linea in resumenes:
        print(linea)

    print("\n--- Análisis ---")
    for linea in analizar(indicadores_con_puntos):
        print(linea)


if __name__ == "__main__":
    run()
