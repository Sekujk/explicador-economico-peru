"""Corre el pipeline completo: extract -> transform -> load -> resumen.

Orquestado con Prefect: cada indicador se extrae y carga como una tarea
independiente con reintentos automáticos (las APIs externas pueden fallar
de forma transitoria), dentro de un flow que se puede correr una vez
(`python -m src.main`) o programar (ver README, sección "Scheduling").
"""

from datetime import date, timedelta

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE

from src.config import INDICADORES, Indicador
from src.db import get_engine, init_schema
from src.extract import bcrp, commodities
from src.load import cargar_indicador
from src.transform import calcular_variaciones, ordenar_y_deduplicar

_LOOKBACK_DIAS = {"diaria": 180, "mensual": 730}


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


@flow(name="explicador-economico-pipeline", log_prints=True)
def run() -> None:
    logger = get_run_logger()
    engine = get_engine()
    init_schema(engine)

    resumenes = []
    for indicador in INDICADORES:
        puntos = extraer(indicador)
        cantidad_cargada = cargar(engine, indicador, puntos)

        con_variacion = calcular_variaciones(puntos)
        resumenes.append(_resumen(indicador.nombre, indicador.unidad, con_variacion))

        logger.info(f"[{indicador.codigo_interno}] {cantidad_cargada} puntos cargados.")

    print("\n--- Resumen del día ---")
    for linea in resumenes:
        print(linea)


if __name__ == "__main__":
    run()
