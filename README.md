# Explicador Económico del Perú

Pipeline en Python que descarga indicadores económicos reales del Perú (tipo de cambio, inflación, tasa de referencia del BCRP, y precio del cobre), los guarda en PostgreSQL con un modelo de datos tipo estrella, y arma un resumen diario con las variaciones, un forecast simple y alertas de valores atípicos.

Lo armé para tener un proyecto propio de Data Engineering con datos reales en vez de un dataset de tutorial: pipeline orquestado con Prefect, tests contra una base de datos real, y CI en GitHub Actions.

## Fuentes de datos

| Indicador | Fuente | Código | Frecuencia |
|---|---|---|---|
| Tipo de cambio interbancario (venta, S/ por US$) | [API BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api) | `PD04638PD` | Diaria |
| Inflación (IPC, variación % interanual) | API BCRP | `PN01273PM` | Mensual |
| Tasa de referencia de política monetaria | API BCRP | `PD04722MM` | Mensual |
| Precio del cobre (futuro, USD/lb) | Yahoo Finance (`yfinance`) | `HG=F` | Diaria |

Ninguna fuente pide API key.

## Setup

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Base de datos

```bash
docker compose up -d db
```

### Correr el pipeline

```bash
python -m src.main
```

Crea el esquema si no existe, descarga los últimos datos de cada indicador, y hace upsert en Postgres (correrlo varias veces no duplica nada).

### Correr todo en Docker

```bash
docker compose run --rm pipeline
```

### Tests

```bash
pytest                        # unitarios + integración (necesita Postgres corriendo)
pytest -m "not integration"   # solo unitarios, sin depender de la base de datos
```

## Orquestación

El pipeline corre como un flow de [Prefect](https://docs.prefect.io/): cada indicador se extrae y carga como una tarea independiente, con reintentos automáticos si falla la conexión a alguna API. `python -m src.main` sigue funcionando igual, ahora con esa capa de confiabilidad.

Para dejarlo corriendo con un cron propio (por ejemplo, todos los días a las 8am) en vez de un cron externo:

```python
from src.main import run

if __name__ == "__main__":
    run.serve(name="explicador-economico-diario", cron="0 8 * * *")
```

Esto abre un proceso que dispara el flow según el cron — pensado para un servidor, no para dejarlo abierto en una laptop.

## CI

`.github/workflows/test.yml` corre toda la suite de tests en cada push, levantando su propio Postgres como servicio del runner (no depende de tener Docker en el CI).

## Análisis

Después de cargar los datos, el pipeline calcula tres cosas más (`src/analysis.py`), usando solo el módulo `statistics` de la librería estándar de Python:

- **Forecast simple:** regresión lineal sobre el histórico de cada indicador para estimar el próximo valor y su tendencia.
- **Detección de anomalías:** compara el último valor contra la media y desviación estándar del resto de la serie (z-score). Si el histórico no tiene varianza (por ejemplo, una tasa que estuvo fija varios meses), lo reporta como no evaluable en vez de forzar una respuesta.
- **Correlación:** entre el tipo de cambio y el precio del cobre. Perú es un exportador grande de cobre, así que hay una relación económica real detrás de ese número, no es arbitrario.

## Modelo de datos

```
dim_indicador (id, codigo_interno, codigo_bcrp, nombre, unidad, fuente, frecuencia)
fact_valor    (id, indicador_id -> dim_indicador.id, fecha, valor)   UNIQUE(indicador_id, fecha)
```

Esquema tipo estrella: una tabla de dimensión (qué indicador es) y una de hechos (su valor en el tiempo), para poder sumar más indicadores sin tocar la estructura.
