"""Carga (upsert) de indicadores y sus valores en la base de datos."""

from datetime import date

from sqlalchemy.engine import Engine

from src.config import Indicador
from src.db import upsert_indicador, upsert_valores


def cargar_indicador(engine: Engine, indicador: Indicador, puntos: list[tuple[date, float]]) -> int:
    """Hace upsert del indicador y sus valores. Devuelve la cantidad de puntos cargados."""
    indicador_id = upsert_indicador(engine, indicador)
    return upsert_valores(engine, indicador_id, puntos)
