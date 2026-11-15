# Alert rules / Reglas de alerta

Issue: BACKEND-05 / #15. Code: `backend/app/services/alert_rules.py` (configuration)
and `backend/app/services/alert_engine.py` (evaluation). Baseline: see
[analysis.md](analysis.md).

- [English](#english)
- [Español](#español)

## English

### The rule: `DEMO-HR-CHANGE`, version `fixture-1`

| Parameter | Value |
| --- | --- |
| Indicator / unit | `heart_rate_bpm`, beats/min |
| Comparable context | `rest` readings only |
| Reference | the #14 heart-rate baseline (days 1-5 mean) of that astronaut |
| Threshold | baseline + 5 beats/min |
| Persistence | 2 consecutive mission days after the reference window |
| Severity | `warning` |

**Simulation assumption.** The +5 beats/min threshold and the two days are a
simulation assumption for the demo. They do not come from clinical sources or
NASA, and they are not validated criteria for astronauts. DATA-06 will review
the evidence later.

- A day's value is the mean of its resting readings observed so far.
- **Detection:** both the previous day and the current day reach the threshold.
  One elevated day never triggers.
- `observed_value` = mean of the resting readings of both days;
  `baseline_value` = the baseline.
- `timestamp`/`mission_day` = the reading that completes the condition;
  `window_start` = first reading of the two days; `window_end` = `timestamp`.
- **Resolution:** a later day whose value is below the threshold sets
  `status="resolved"` and `resolved_at` = that reading's time. A new event then
  needs two elevated days after the resolution day.
- Provenance comes from the reading that completed the condition.
- Text is observational and in English; no diagnosis or treatment.
- If the baseline is not `available` at the cutoff, the rule is not evaluated
  and the status is `insufficient_data`, never "no alerts".

### With the seed (`AST-001`, baseline 72)

- Cutoff day 6 (`2026-11-06T23:59:59Z`): day 6 is 78 but alone →
  `available`, 0 alerts.
- Cutoff day 7 (`2026-11-07T23:59:59Z`): days 6-7 are 78 and 84 →
  one active `warning` alert, `observed_value` 81, window
  `2026-11-06T12:00:00Z` → `2026-11-07T12:00:00Z`. It equals the fixture
  `explainable_synthetic_alert` (only `alert_id` is generated).
- Cutoff day 5 or `AST-002`: `insufficient_data`.

### Evaluation, deduplication and `as_of`

- The evaluator is deterministic: it walks the stored history in
  (timestamp, ID) order and each event uses only data at or before its
  detection. It runs after every reading/journal write, after an import, and
  before answering `GET /alerts` and `GET /summary`.
- Alerts are saved with the event-key upsert
  (astronaut, rule, version, indicator, timestamp): re-running never copies
  and keeps `alert_id`.
- A view at `as_of` returns alerts detected at or before it. One resolved
  after `as_of` reads as `active` with `resolved_at=null`.
- `evaluation_status` is `available` when the baseline is available at the
  cutoff (with or without alerts), otherwise `insufficient_data` with
  `active_count`/`highest_severity` null and `recent` empty.

### Limits

One rule only. Not a diagnosis, not clinically validated. No acknowledgement
or manual resolution. The fixture cutoff `2026-11-05T23:59:59Z` shows an
available evaluation; under the #14 policy the baseline is available from day
6, so the API returns `insufficient_data` there.

## Español

### La regla: `DEMO-HR-CHANGE`, versión `fixture-1`

| Parámetro | Valor |
| --- | --- |
| Indicador / unidad | `heart_rate_bpm`, beats/min |
| Contexto comparable | solo lecturas `rest` |
| Referencia | el baseline de frecuencia cardíaca del #14 (media días 1-5) del astronauta |
| Umbral | baseline + 5 beats/min |
| Persistencia | 2 días de misión consecutivos posteriores a la ventana de referencia |
| Severidad | `warning` |

**Suposición de simulación.** El umbral de +5 beats/min y los dos días son una
suposición de simulación para la demo. No proceden de fuentes clínicas ni de
NASA y no son criterios validados para astronautas. DATA-06 revisará la
evidencia después.

- El valor de un día es la media de sus lecturas de reposo observadas hasta ese
  momento.
- **Detección:** el día anterior y el día actual alcanzan el umbral. Un solo
  día elevado nunca la activa.
- `observed_value` = media de las lecturas de reposo de ambos días;
  `baseline_value` = el baseline.
- `timestamp`/`mission_day` = la lectura que completa la condición;
  `window_start` = primera lectura de los dos días; `window_end` = `timestamp`.
- **Resolución:** un día posterior con valor por debajo del umbral pone
  `status="resolved"` y `resolved_at` = la hora de esa lectura. Un nuevo evento
  necesita después dos días elevados posteriores al día de resolución.
- La procedencia es la de la lectura que completó la condición.
- Los textos son observacionales y en inglés; sin diagnóstico ni tratamiento.
- Si el baseline no está `available` en el corte, la regla no se evalúa y el
  estado es `insufficient_data`, nunca "sin alertas".

### Con la semilla (`AST-001`, baseline 72)

- Corte día 6 (`2026-11-06T23:59:59Z`): el día 6 vale 78 pero es uno solo →
  `available`, 0 alertas.
- Corte día 7 (`2026-11-07T23:59:59Z`): los días 6-7 valen 78 y 84 → una
  alerta `warning` activa, `observed_value` 81, ventana
  `2026-11-06T12:00:00Z` → `2026-11-07T12:00:00Z`. Coincide con el fixture
  `explainable_synthetic_alert` (solo `alert_id` es generado).
- Corte día 5 o `AST-002`: `insufficient_data`.

### Evaluación, deduplicación y `as_of`

- El evaluador es determinista: recorre la historia guardada en orden
  (timestamp, ID) y cada evento usa solo datos hasta su detección. Se ejecuta
  tras cada escritura de lectura o diario, tras una importación y antes de
  responder `GET /alerts` y `GET /summary`.
- Las alertas se guardan con el upsert por clave de evento
  (astronauta, regla, versión, indicador, timestamp): repetir no crea copias y
  conserva `alert_id`.
- Una vista en `as_of` devuelve las alertas detectadas hasta ese momento. Una
  resuelta después de `as_of` aparece `active` con `resolved_at=null`.
- `evaluation_status` es `available` si el baseline está disponible en el corte
  (con o sin alertas); si no, `insufficient_data` con
  `active_count`/`highest_severity` null y `recent` vacío.

### Límites

Una sola regla. No es diagnóstico ni está validada clínicamente. Sin
reconocimiento ni resolución manual. El fixture con corte
`2026-11-05T23:59:59Z` muestra una evaluación disponible; con la política del
#14 el baseline está disponible desde el día 6, así que la API devuelve
`insufficient_data` en ese corte.
