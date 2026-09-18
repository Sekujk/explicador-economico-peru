"""Esquema y acceso a la base de datos (modelo tipo estrella simple)."""

from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL, Indicador

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_indicador (
    id SERIAL PRIMARY KEY,
    codigo_interno VARCHAR(50) UNIQUE NOT NULL,
    codigo_fuente VARCHAR(20) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    unidad VARCHAR(50) NOT NULL,
    fuente VARCHAR(20) NOT NULL,
    frecuencia VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_valor (
    id SERIAL PRIMARY KEY,
    indicador_id INTEGER NOT NULL REFERENCES dim_indicador(id),
    fecha DATE NOT NULL,
    valor NUMERIC(18, 6) NOT NULL,
    UNIQUE (indicador_id, fecha)
);
"""


def get_engine() -> Engine:
    return create_engine(DATABASE_URL)


def init_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(_SCHEMA))


def upsert_indicador(engine: Engine, indicador: Indicador) -> int:
    stmt = text(
        """
        INSERT INTO dim_indicador (codigo_interno, codigo_fuente, nombre, unidad, fuente, frecuencia)
        VALUES (:codigo_interno, :codigo_fuente, :nombre, :unidad, :fuente, :frecuencia)
        ON CONFLICT (codigo_interno) DO UPDATE SET
            codigo_fuente = EXCLUDED.codigo_fuente,
            nombre = EXCLUDED.nombre,
            unidad = EXCLUDED.unidad,
            fuente = EXCLUDED.fuente,
            frecuencia = EXCLUDED.frecuencia
        RETURNING id
        """
    )
    with engine.begin() as conn:
        resultado = conn.execute(
            stmt,
            {
                "codigo_interno": indicador.codigo_interno,
                "codigo_fuente": indicador.codigo_fuente,
                "nombre": indicador.nombre,
                "unidad": indicador.unidad,
                "fuente": indicador.fuente,
                "frecuencia": indicador.frecuencia,
            },
        )
        return resultado.scalar_one()


def upsert_valores(engine: Engine, indicador_id: int, puntos: list[tuple[date, float]]) -> int:
    if not puntos:
        return 0

    stmt = text(
        """
        INSERT INTO fact_valor (indicador_id, fecha, valor)
        VALUES (:indicador_id, :fecha, :valor)
        ON CONFLICT (indicador_id, fecha) DO UPDATE SET valor = EXCLUDED.valor
        """
    )
    with engine.begin() as conn:
        for fecha, valor in puntos:
            conn.execute(stmt, {"indicador_id": indicador_id, "fecha": fecha, "valor": valor})

    return len(puntos)
