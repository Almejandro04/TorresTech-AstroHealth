# Backend tests / Pruebas del backend

Issue: BACKEND-07 / #18.

- [English](#english)
- [Español](#español)

## English

### Run

From the repository root, once:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Then, from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest
```

Warnings are errors (`pytest.ini`). No network, downloads or private data are
used. An autouse fixture in `tests/conftest.py` points `ASTROHEALTH_DB_PATH`
at a `tmp_path` file, so no test touches a working database
(`tests/test_regressions.py` checks this).

### Coverage

| Area | Modules | What is covered |
| --- | --- | --- |
| Health, CORS, OpenAPI | `test_health.py`, `test_api.py` | Health envelope; allowed and refused origins; every endpoint, model and example in Swagger |
| API | `test_api.py` | All 24 shared fixture cases; ordering, pagination, day filters, `as_of`; 404/405/409/422/500 envelopes; persistence across restarts |
| Validation | `test_models.py`, `test_database.py`, `test_api.py` | Strict types, ranges, UTC timestamps, required/nullable fields, mission day, unknown profile or source; null vs zero |
| Storage | `test_database.py`, `test_seed.py` | Uniqueness, retries, conflicts, journal upsert, alert upsert/resolution, atomic and deterministic seed/reset |
| Ingestion | `test_ingestion.py` | Valid JSON/CSV, invalid bundles rolled back, idempotent re-import, staged replay cutoffs |
| Calculation | `test_analysis.py`, `test_analysis_api.py` | Hand-calculated means, std, deltas; context/astronaut/unit separation; insufficient history; zero variance and zero reference |
| Alerts | `test_alerts.py`, `test_regressions.py` | Normal day, isolated spike, sustained change, missing data, other contexts, resolution, deduplication, exact explanation |
| Regressions | `test_regressions.py` | Future readings never change a past view (baselines and alerts), intra-day cutoff, isolation |

### Expected failures (strict xfail)

| Case | Reason |
| --- | --- |
| `summary_normal_reference_fixture` | `#14 policy: baseline available from day 6; the fixture shows it at the end of day 5` |
| `evaluated_no_active_alerts` | same as above |
| `summary_before_analysis_is_implemented` | `earlier stage: the fixture shows analysis not implemented` |
| `alerts_not_implemented_is_not_an_all_clear` | same as above |

Their remaining fields are compared in `test_analysis_fixture_case_matches_outside_analysis`.

### Limits

- No browser or UI tests; `backend/scripts/check_frontend_api.mjs` only checks the
  real frontend HTTP client against a running server.
- Baselines and the alert rule are experimental. The tests verify the
  implemented behavior, not clinical validity.

## Español

### Ejecución

Desde la raíz del repositorio, una vez:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Después, desde `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest
```

Los avisos son errores (`pytest.ini`). No se usa red, descargas ni datos
privados. Un fixture automático de `tests/conftest.py` apunta
`ASTROHEALTH_DB_PATH` a un archivo en `tmp_path`, así que ninguna prueba toca
una base de trabajo (`tests/test_regressions.py` lo comprueba).

### Cobertura

| Área | Módulos | Qué cubren |
| --- | --- | --- |
| Health, CORS, OpenAPI | `test_health.py`, `test_api.py` | Sobre de health; orígenes permitidos y rechazados; todos los endpoints, modelos y ejemplos en Swagger |
| API | `test_api.py` | Los 24 casos del fixture compartido; orden, paginación, filtros por día, `as_of`; sobres 404/405/409/422/500; persistencia tras reinicio |
| Validación | `test_models.py`, `test_database.py`, `test_api.py` | Tipos estrictos, rangos, timestamps UTC, campos requeridos/nulables, día de misión, perfil o fuente desconocidos; null frente a cero |
| Almacenamiento | `test_database.py`, `test_seed.py` | Unicidad, reenvíos, conflictos, upsert del diario, upsert/resolución de alertas, semilla y reset atómicos y deterministas |
| Ingestión | `test_ingestion.py` | JSON/CSV válidos, paquetes inválidos revertidos, reimportación idempotente, cortes de replay por etapas |
| Cálculo | `test_analysis.py`, `test_analysis_api.py` | Medias, desviación y deltas calculados a mano; separación por contexto, astronauta y unidad; historia insuficiente; varianza y referencia cero |
| Alertas | `test_alerts.py`, `test_regressions.py` | Día normal, pico aislado, cambio sostenido, datos faltantes, otros contextos, resolución, deduplicación, explicación exacta |
| Regresiones | `test_regressions.py` | Lecturas futuras nunca cambian una vista pasada (baselines y alertas), corte dentro del día, aislamiento |

### Fallos esperados (xfail estrictos)

| Caso | Motivo |
| --- | --- |
| `summary_normal_reference_fixture` | `#14 policy: baseline available from day 6; the fixture shows it at the end of day 5` |
| `evaluated_no_active_alerts` | igual que el anterior |
| `summary_before_analysis_is_implemented` | `earlier stage: the fixture shows analysis not implemented` |
| `alerts_not_implemented_is_not_an_all_clear` | igual que el anterior |

Sus demás campos se comparan en `test_analysis_fixture_case_matches_outside_analysis`.

### Límites

- Sin pruebas de navegador ni de interfaz; `backend/scripts/check_frontend_api.mjs`
  solo prueba el cliente HTTP real del frontend contra un servidor en marcha.
- Los baselines y la regla de alertas son experimentales. Las pruebas verifican el
  comportamiento implementado, no su validez clínica.
