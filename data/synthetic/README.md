# Synthetic 30-day mission / Misión sintética de 30 días

Issue: DATA-04 / #6. Source: `SYN-AH-MISSION-001` (`source_type = "synthetic"`).

- [English](#english)
- [Español](#español)

## English

### Regenerate

From the repository root (no network; seed 2026 by default):

```powershell
.\.venv\Scripts\python.exe data\scripts\generate_synthetic_mission.py --seed 2026 --start-date 2026-11-01
```

The same arguments always produce byte-identical files (`random.Random(seed)`,
fixed JSON formatting and `\n` line endings). `data/tests/test_synthetic_mission.py`
checks that the committed files match a fresh generation.

### Files

| File | Content |
| --- | --- |
| `mission_ast101_ast102.json` | Bundle for `import-json` |
| `mission_manifest.json`, `readings.csv`, `journal.csv` | The same records for `import-csv` |
| `scenario_manifest.json` | Reference days, introduced changes and the expected rule result |
| `fixtures/*.json` | Small independent bundles: `normal` (AST-201), `sustained_deviation` (AST-202), `isolated_spike` (AST-203), `missing_values` (AST-204), `insufficient_history` (AST-205) |

### What is artificial

Everything. Fictional astronauts `AST-101` (30 days) and `AST-102` (days 1-3 only,
insufficient history), with IDs that do not collide with the contract seed
(`AST-001`, `AST-002`). Reference values are `[SIMULATION-ASSUMPTION]`s chosen inside
published ranges:

| Value | Rest | Sleep (even days, 03:00Z) | Exercise (even days, 17:00Z) | Basis |
| --- | --- | --- | --- | --- |
| Heart rate (beats/min) | 72 ± 1 | 56 ± 1 | 110 ± 3 | Near in-flight daytime HR and night HR ~55.7 (S4); within 60–100 (S15). Exercise value is illustrative, no source |
| SpO2 (%) | 98 (−1/0) | 97 | 97 | 96–100 (S16) |
| Respiratory rate (breaths/min) | 15 ± 1 | 14 | 22 | 12–16 (S15). Exercise value is illustrative, no source |
| Sleep (h, journal 08:00Z) | 6.5 ± 0.25 | | | Near ~6.1 h in flight (S3), slightly higher to leave room for the reduction |
| Mood (1–5) | 4, sometimes 3 | | | Product scale, not a clinical scale |

AST-101 scenario: days 1–5 stable reference; day 9 isolated spike (rest HR = base + 12);
day 12 rest HR null; day 13 rest RR null; day 14 no journal entry; days 18–21 sustained
rest HR = base + 8 (± 1); day 22 return to base; days 18–23 sleep 5.0–5.5 h, mood 2 and
rest SpO2 97 (artificial pattern consistent in direction with S3/S12, no causal claim);
days 24–30 recovery. Expected with the backend rule: no alert on day 9, detection on
day 19 (days 18–19), resolution on day 22, AST-102 `insufficient_data`.

### Limitations

Not a validated physiological model, not astronaut data and not clinically validated.
The +5 beats/min rule threshold is itself a simulation assumption.

### Import

```powershell
$env:ASTROHEALTH_DB_PATH = "$env:TEMP\astrohealth-mission30.db"
cd backend
..\.venv\Scripts\python.exe -m app.database import-json ..\data\synthetic\mission_ast101_ast102.json --until-day 30
```

To create new journal entries from the frontend with this mission:
`VITE_JOURNAL_SOURCE_ID=SYN-AH-MISSION-001` and `VITE_JOURNAL_TIME_UTC=08:00:00`.

## Español

### Regenerar

Desde la raíz del repositorio (sin red; semilla 2026 por defecto):

```powershell
.\.venv\Scripts\python.exe data\scripts\generate_synthetic_mission.py --seed 2026 --start-date 2026-11-01
```

Los mismos argumentos producen siempre archivos idénticos byte a byte
(`random.Random(seed)`, formato JSON fijo y finales de línea `\n`).
`data/tests/test_synthetic_mission.py` comprueba que los archivos versionados
coinciden con una generación nueva.

### Archivos

| Archivo | Contenido |
| --- | --- |
| `mission_ast101_ast102.json` | Bundle para `import-json` |
| `mission_manifest.json`, `readings.csv`, `journal.csv` | Los mismos registros para `import-csv` |
| `scenario_manifest.json` | Días de referencia, cambios introducidos y resultado esperado de la regla |
| `fixtures/*.json` | Bundles pequeños independientes: `normal` (AST-201), `sustained_deviation` (AST-202), `isolated_spike` (AST-203), `missing_values` (AST-204), `insufficient_history` (AST-205) |

### Qué es artificial

Todo. Astronautas ficticios `AST-101` (30 días) y `AST-102` (solo días 1-3, historia
insuficiente), con IDs que no chocan con la semilla del contrato (`AST-001`, `AST-002`).
Los valores de referencia son `[SIMULATION-ASSUMPTION]` elegidos dentro de rangos
publicados:

| Valor | Reposo | Sueño (días pares, 03:00Z) | Ejercicio (días pares, 17:00Z) | Base |
| --- | --- | --- | --- | --- |
| Frecuencia cardíaca (beats/min) | 72 ± 1 | 56 ± 1 | 110 ± 3 | Cerca de la FC diurna en vuelo y de la FC nocturna ~55.7 (S4); dentro de 60–100 (S15). El valor de ejercicio es ilustrativo, sin fuente |
| SpO2 (%) | 98 (−1/0) | 97 | 97 | 96–100 (S16) |
| Frecuencia respiratoria (breaths/min) | 15 ± 1 | 14 | 22 | 12–16 (S15). El valor de ejercicio es ilustrativo, sin fuente |
| Sueño (h, diario 08:00Z) | 6.5 ± 0.25 | | | Cerca de ~6.1 h en vuelo (S3), algo mayor para dejar margen a la reducción |
| Ánimo (1–5) | 4, a veces 3 | | | Escala del producto, no una escala clínica |

Escenario de AST-101: días 1–5 referencia estable; día 9 pico aislado (FC en reposo =
base + 12); día 12 FC en reposo null; día 13 FR en reposo null; día 14 sin entrada de
diario; días 18–21 FC en reposo sostenida = base + 8 (± 1); día 22 vuelta a la base;
días 18–23 sueño 5.0–5.5 h, ánimo 2 y SpO2 en reposo 97 (patrón artificial coherente en
dirección con S3/S12, sin afirmar causalidad); días 24–30 recuperación. Resultado
esperado con la regla del backend: sin alerta el día 9, detección el día 19 (días 18–19),
resolución el día 22, AST-102 `insufficient_data`.

### Limitaciones

No es un modelo fisiológico validado, no son datos de astronautas y no está validado
clínicamente. El umbral de +5 beats/min de la regla es también un supuesto de simulación.

### Importar

```powershell
$env:ASTROHEALTH_DB_PATH = "$env:TEMP\astrohealth-mission30.db"
cd backend
..\.venv\Scripts\python.exe -m app.database import-json ..\data\synthetic\mission_ast101_ast102.json --until-day 30
```

Para crear entradas nuevas del diario desde el frontend con esta misión:
`VITE_JOURNAL_SOURCE_ID=SYN-AH-MISSION-001` y `VITE_JOURNAL_TIME_UTC=08:00:00`.
