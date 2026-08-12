# Explicador Económico del Perú

Pipeline que descarga indicadores económicos reales (BCRP + precio del cobre), los normaliza en un modelo de datos tipo estrella, y calcula variaciones/estadística básica. Fase 1 del proyecto: ETL + modelo de datos + Docker. Ver el plan completo (fases 2-4: orquestador, análisis avanzado, API + frontend) en `wiki/code/explicador-economico.md` del vault.

## Fuentes de datos (verificadas, sin API key)

| Indicador | Fuente | Código | Frecuencia |
|---|---|---|---|
| Tipo de cambio interbancario (venta, S/ por US$) | [API BCRP](https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api) | `PD04638PD` | Diaria |
| Inflación (IPC, variación % interanual) | API BCRP | `PN01273PM` | Mensual |
| Tasa de referencia de política monetaria | API BCRP | `PD04722MM` | Mensual |
| Precio del cobre (futuro, USD/lb) | Yahoo Finance (`yfinance`) | `HG=F` | Diaria |

La API del BCRP no requiere key. `yfinance` tampoco. Cero fricción para arrancar.

> Los tres códigos del BCRP fueron verificados contra el sitio oficial de BCRPData antes de usarlos (no están inventados). Si se agregan más series, buscar el código real en <https://estadisticas.bcrp.gob.pe/estadisticas/series/> antes de hardcodearlo en `src/config.py`.

## Setup

```bash
cp .env.example .env
# Windows: python -m venv .venv && .venv\Scripts\activate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Levantar la base de datos (Docker)

```bash
docker compose up -d db
```

### Correr el pipeline (extract -> transform -> load)

```bash
python -m src.main
```

Esto crea el esquema si no existe, descarga los últimos datos de cada indicador, y hace upsert en Postgres (no duplica si vuelves a correrlo el mismo día).

### Correr el pipeline dentro de Docker (en vez de local)

```bash
docker compose run --rm pipeline
```

### Tests

```bash
pytest              # unitarios + integración (requiere `docker compose up -d db` corriendo)
pytest -m "not integration"   # solo unitarios, sin depender de la base de datos
```

## Orquestación (Prefect)

El pipeline está decorado como un flow de [Prefect](https://docs.prefect.io/): cada indicador se extrae y carga como una tarea independiente, con reintentos automáticos (3 para extracción, 2 para carga) ante fallos transitorios de red. Correrlo con `python -m src.main` sigue funcionando igual que antes, ahora con esa capa de confiabilidad.

Para programarlo (ej. correr todos los días a las 8am), en vez de un cron externo se puede usar el scheduling nativo de Prefect:

```python
from src.main import run

if __name__ == "__main__":
    run.serve(name="explicador-economico-diario", cron="0 8 * * *")
```

Esto deja un proceso corriendo que dispara el flow según el cron — pensado para correr en un servidor/VM, no para dejarlo abierto en una laptop.

## CI (GitHub Actions)

`.github/workflows/test.yml` corre toda la suite de tests (unitarios + integración) en cada push/PR, levantando un Postgres real como servicio de CI — no hace falta Docker en el runner. Requiere que el proyecto esté en un repositorio de GitHub para activarse.

## Modelo de datos

```
dim_indicador (id, codigo_interno, codigo_bcrp, nombre, unidad, fuente, frecuencia)
fact_valor    (id, indicador_id -> dim_indicador.id, fecha, valor)   UNIQUE(indicador_id, fecha)
```

Esquema tipo estrella simple: una tabla de dimensión (qué indicador es) y una de hechos (su valor en el tiempo), pensado para poder agregar más indicadores sin cambiar la estructura.

## Roadmap

- [x] Fase 1: ETL + modelo de datos + Docker (verificada de punta a punta contra Postgres real, 291 registros cargados).
- [x] Fase 2: orquestador (Prefect), tests de integración, CI en GitHub Actions.
- [ ] Fase 3: correlación entre indicadores, forecast simple, detección de anomalías.
- [ ] Fase 4: API en FastAPI + página en el Portafolio Web consumiéndola.
