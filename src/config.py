import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://explicador:changeme@localhost:5432/explicador_economico",
)


@dataclass(frozen=True)
class Indicador:
    codigo_interno: str
    nombre: str
    unidad: str
    fuente: str  # "BCRP" | "yfinance"
    frecuencia: str  # "diaria" | "mensual"
    codigo_fuente: str  # código BCRP o ticker de yfinance


# Códigos BCRP verificados contra https://estadisticas.bcrp.gob.pe/estadisticas/series/
# antes de usarlos aquí. Si agregas un indicador nuevo, verifica el código real primero.
INDICADORES = [
    Indicador(
        codigo_interno="tipo_cambio_venta",
        nombre="Tipo de cambio interbancario, venta",
        unidad="S/ por US$",
        fuente="BCRP",
        frecuencia="diaria",
        codigo_fuente="PD04638PD",
    ),
    Indicador(
        codigo_interno="inflacion_interanual",
        nombre="Inflación (IPC, variación % interanual)",
        unidad="% var. 12 meses",
        fuente="BCRP",
        frecuencia="mensual",
        codigo_fuente="PN01273PM",
    ),
    Indicador(
        codigo_interno="tasa_referencia",
        nombre="Tasa de referencia de política monetaria",
        unidad="%",
        fuente="BCRP",
        frecuencia="mensual",
        codigo_fuente="PD04722MM",
    ),
    Indicador(
        codigo_interno="precio_cobre",
        nombre="Precio del cobre (futuro)",
        unidad="USD/lb",
        fuente="yfinance",
        frecuencia="diaria",
        codigo_fuente="HG=F",
    ),
]
