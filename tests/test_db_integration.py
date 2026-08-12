"""Tests de integración: requieren una base de datos Postgres real corriendo
(`docker compose up -d db` local, o el servicio `postgres` en CI).
"""

from datetime import date

import pytest
from sqlalchemy import text

from src.config import Indicador
from src.db import get_engine, init_schema, upsert_indicador, upsert_valores

pytestmark = pytest.mark.integration

_INDICADOR_PRUEBA = Indicador(
    codigo_interno="test_indicador",
    nombre="Indicador de prueba",
    unidad="unidad",
    fuente="TEST",
    frecuencia="diaria",
    codigo_fuente="TEST01",
)


@pytest.fixture
def engine():
    eng = get_engine()
    init_schema(eng)
    yield eng
    with eng.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM fact_valor WHERE indicador_id IN "
                "(SELECT id FROM dim_indicador WHERE codigo_interno = :codigo)"
            ),
            {"codigo": _INDICADOR_PRUEBA.codigo_interno},
        )
        conn.execute(
            text("DELETE FROM dim_indicador WHERE codigo_interno = :codigo"),
            {"codigo": _INDICADOR_PRUEBA.codigo_interno},
        )


def _contar_valores(engine, indicador_id: int) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT COUNT(*) FROM fact_valor WHERE indicador_id = :id"),
            {"id": indicador_id},
        ).scalar_one()


def test_upsert_indicador_es_idempotente(engine):
    id_1 = upsert_indicador(engine, _INDICADOR_PRUEBA)
    id_2 = upsert_indicador(engine, _INDICADOR_PRUEBA)

    assert id_1 == id_2  # mismo codigo_interno -> mismo id, no crea un duplicado


def test_upsert_valores_no_duplica_al_cargar_dos_veces(engine):
    indicador_id = upsert_indicador(engine, _INDICADOR_PRUEBA)
    puntos = [(date(2026, 1, 1), 10.0), (date(2026, 1, 2), 20.0)]

    upsert_valores(engine, indicador_id, puntos)
    upsert_valores(engine, indicador_id, puntos)  # misma carga, otra vez

    assert _contar_valores(engine, indicador_id) == 2


def test_upsert_valores_actualiza_el_valor_si_la_fecha_se_repite(engine):
    indicador_id = upsert_indicador(engine, _INDICADOR_PRUEBA)

    upsert_valores(engine, indicador_id, [(date(2026, 1, 1), 10.0)])
    upsert_valores(engine, indicador_id, [(date(2026, 1, 1), 99.0)])  # mismo día, valor corregido

    with engine.begin() as conn:
        valor = conn.execute(
            text("SELECT valor FROM fact_valor WHERE indicador_id = :id"),
            {"id": indicador_id},
        ).scalar_one()

    assert float(valor) == 99.0
    assert _contar_valores(engine, indicador_id) == 1
