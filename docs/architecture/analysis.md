# Baseline and trend analysis / Análisis de referencias y tendencias

Issue: BACKEND-04 / #14. Code: `backend/app/services/analysis.py`.
Contract: [`docs/api_contract.md`](../api_contract.md) v0.1.0, section 3.5.

- [English](#english)
- [Español](#español)

## English

### What this is, and what it is not

These are small, reproducible demonstration statistics over synthetic data for
fictional astronauts. They are not a diagnosis, a clinical score, a medical
threshold, or a validated model. The window and the minimums below are a
**provisional experimental decision** made so the prototype can be reviewed.
The team has not agreed a scientific reference policy, and these choices are
pending team review before merge. They are not taken from any space agency or
medical source.

### Indicators, contexts and units

| Indicator | Records used | Context | Unit |
| --- | --- | --- | --- |
| `heart_rate_bpm` | readings | `rest` only | beats/min |
| `spo2_percent` | readings | `rest` only | % |
| `respiratory_rate_bpm` | readings | `rest` only | breaths/min |
| `sleep_hours_last_night` | daily journal | none (null) | hours |

- `mood_score` is an ordinal self-report. It has no mean, reference, trend or
  score, as the contract defers those calculations.
- A series is one astronaut, one indicator and one measurement context.
  `rest`, `exercise`, `sleep` and `unknown` readings are never combined, and
  neither are astronauts. The summary uses `rest`; the internal functions can
  analyze another context on its own.
- Journal entries (one per mission day) and point-in-time readings are separate
  series with separate cadence.
- Units come from the contract's field names. The analysis rejects a series
  whose observations carry different units or a unit other than the
  indicator's. It never converts measurements.

### Provisional reference policy

| Setting | Value |
| --- | --- |
| Reference window | mission days 1 to 5, fixed |
| Statistic | arithmetic mean of the non-null values in the window |
| Minimum | 5 observations on 5 distinct mission days |
| Available from | the cutoff's mission day is 6 or later |
| Method name | `experimental_fixed_window_mean_v1` |

- Until the cutoff reaches day 6 the window may still receive data, so the
  reference is not declared, even if it already holds 5 observations.
- Observations after day 5 never update the reference.
- If the window does not hold enough data, the result is `insufficient_data`.
  The window is never widened with later days.
- Distinct days are counted separately from observations: five readings on one
  day are 5 observations on 1 day, which is not enough.

### Formulas

For the values `x1 … xn` of one series:

- **Mean:** `mean = (x1 + … + xn) / n`
- **Population standard deviation:** `std = sqrt(((x1 - mean)² + … + (xn - mean)²) / n)`.
  The denominator is `n`, not `n - 1`.
- **Minimum, maximum, count:** over the same values.
- With no values, the count is 0 and every other statistic is absent (null),
  not 0.

Reference: `reference = mean of the window's values`. `sample_count` is the
number of observations used.

Daily trend, for each mission day that has observations:

- `daily_mean = mean of that day's values`
- `delta = daily_mean - reference`
- `percent_change = 100 * delta / reference`, only when the reference is not 0

There is no regression, smoothing, z-score, prediction or threshold. The daily
mean is an internal aggregate. It never replaces stored records and never adds
points to a history.

### Worked examples

**Reference.** Resting heart rate on days 1-5: 76, 78, 80, 82, 84.
Sum 400, `400 / 5 = 80`. Reference = 80 beats/min, 5 observations, 5 days.

**Trend.** Day 6 has two resting readings, 86 and 90: daily mean
`(86 + 90) / 2 = 88`. `delta = 88 - 80 = 8`. `percent_change = 100 * 8 / 80 = 10`.
Day 7 has one reading of 72: `delta = -8`, `percent_change = -10`.

**Standard deviation.** Values 2, 4, 4, 4, 5, 5, 7, 9: sum 40, mean 5.
Squared deviations 9, 1, 1, 1, 0, 0, 4, 16 add up to 32. `32 / 8 = 4`,
`sqrt(4) = 2`.

**Demo seed.** `AST-001` has 72 beats/min, 98 %, 16 breaths/min and 7.5 h on
each of days 1-5, so the references are 72, 98, 16 and 7.5 with 5 samples each.

Results are not rounded. Tests compare exact values where the arithmetic is
exact in binary and use a relative tolerance of `1e-9` otherwise.

### Missing values, extremes and duplicates

- `null` means absent and takes no part in any calculation. A valid zero (for
  example 0 hours of sleep) is a value and does take part.
- Unusual but well-formed values are kept. No outlier is removed.
- An identical retry or re-import of a reading does not create a second row,
  so it cannot add weight. Inside the analysis, a record that appears twice
  (same record ID) is also counted once.
- Two different records with the same timestamp are two observations. Storage
  already forbids two readings of one astronaut with the same timestamp and
  context, and more than one journal entry per day. Ties are ordered by ID.
- Timestamps are compared exactly, including digits beyond the microsecond.
- No result is NaN or infinite. Non-finite inputs are rejected.

### Zero reference and zero variance

- If every value is the same, the standard deviation is exactly 0 and the mean
  is exactly that value. Nothing is ever divided by the standard deviation.
- A reference of 0 is valid. `delta` is calculated; `percent_change` is
  unavailable with the reason `reference_is_zero`.
- Without a reference, `delta` and `percent_change` are unavailable with the
  reason `reference_unavailable`. Zero is never used as a stand-in.

### Cutoff and reproducibility

- Observations are filtered by `as_of` before any reference, statistic, daily
  mean or trend is calculated. Nothing after the cutoff can affect a result.
- A returned window never ends after `as_of`.
- A cutoff inside a day uses only what was observed up to that instant.
- Adding later observations does not change the result of an earlier cutoff.
- Results are calculated on demand and are not cached, so a write or import
  can never leave a stale analysis.
- **Limitation:** `as_of` is an observation cutoff, not a database version
  history. Correcting a journal entry replaces that day's values, so the
  analysis of that day, and a reference that includes it, can change. The same
  is true of a late import whose timestamps fall inside the window.

### Mapping to `BaselineMetric`

`summary.baselines` keeps its four keys and its existing fields.

| Field | `available` | `insufficient_data` |
| --- | --- | --- |
| `status` | `available` | `insufficient_data` |
| `value` | the mean | null |
| `sample_count` | observations used | valid observations in the window so far |
| `reference_start` | timestamp of the first observation used | null |
| `reference_end` | timestamp of the last observation used | null |
| `measurement_context` | `rest` for vitals, null for sleep | same |
| `method` | `experimental_fixed_window_mean_v1` | null |

`not_implemented` is no longer returned for baselines. The alert summary and
`GET /alerts` stay `not_implemented` until #15.

### Differences from the shared fixtures

The fixtures are illustrative contract examples and were not changed.

- Available fixture baselines use the window's calendar bounds
  (`2026-11-01T00:00:00Z` to `2026-11-05T23:59:59Z`) and
  `method="fixture_reference_mean"`. The API reports the observations actually
  used and its own method name. Status, value, sample count and context match.
- `summary_normal_reference_fixture` uses the cutoff `2026-11-05T23:59:59Z`
  and shows `available`. Under the provisional policy the reference becomes
  available at `2026-11-06T00:00:00Z`; one second earlier the API returns
  `insufficient_data` with the same 5 samples. The frontend mock engine follows
  the fixture. This is the one material difference to settle with the team.

### Pending: exposing trends over HTTP

The contract has no HTTP field for trends or descriptive statistics, so none
was added and no endpoint was created. Minimal proposal to discuss with the
frontend owner before any change:

- One read-only endpoint, `GET /api/astronauts/{id}/trends`, with the existing
  `as_of`, `from_day` and `to_day` parameters.
- `data` keyed by the four baseline indicators. Each holds its `unit`,
  `measurement_context`, and a list of points:
  `mission_day`, `daily_mean`, `sample_count`, `delta`, `percent_change`, and
  `unavailable_reason` (`reference_unavailable`, `reference_is_zero` or null).
- Optional `stats` per indicator: `count`, `mean`, `minimum`, `maximum`,
  `population_std`.

Until that is agreed, charts can already draw the reference line from
`summary.baselines` over the unchanged histories.

### Limits

- Demonstration statistics on synthetic data; no diagnosis, no clinical
  validation, no medical thresholds.
- One fixed window per astronaut; no rolling or adaptive reference.
- The 30-day demonstration dataset (DATA-04) is not required and was not
  generated here.

## Español

### Qué es y qué no es

Son estadísticas de demostración pequeñas y reproducibles sobre datos
sintéticos de astronautas ficticios. No son un diagnóstico, una puntuación
clínica, un umbral médico ni un modelo validado. La ventana y los mínimos
siguientes son una **decisión experimental provisional** adoptada para que el
prototipo pueda revisarse. El equipo no ha acordado una política científica de
referencia y estas decisiones quedan pendientes de revisión antes del merge.
No proceden de ninguna agencia espacial ni fuente médica.

### Indicadores, contextos y unidades

| Indicador | Registros usados | Contexto | Unidad |
| --- | --- | --- | --- |
| `heart_rate_bpm` | lecturas | solo `rest` | beats/min |
| `spo2_percent` | lecturas | solo `rest` | % |
| `respiratory_rate_bpm` | lecturas | solo `rest` | breaths/min |
| `sleep_hours_last_night` | diario | ninguno (null) | hours |

- `mood_score` es un autoinforme ordinal. No tiene media, referencia, tendencia
  ni puntuación, porque el contrato difiere esos cálculos.
- Una serie es un astronauta, un indicador y un contexto de medición. Las
  lecturas `rest`, `exercise`, `sleep` y `unknown` nunca se combinan, y los
  astronautas tampoco. El summary usa `rest`; las funciones internas pueden
  analizar otro contexto por separado.
- Las entradas de diario (una por día de misión) y las lecturas puntuales son
  series distintas con cadencia distinta.
- Las unidades provienen de los nombres de campo del contrato. El análisis
  rechaza una serie cuyas observaciones traigan unidades distintas o una unidad
  que no sea la del indicador. Nunca convierte mediciones.

### Política provisional de referencia

| Parámetro | Valor |
| --- | --- |
| Ventana de referencia | días de misión 1 a 5, fija |
| Estadístico | media aritmética de los valores no nulos de la ventana |
| Mínimo | 5 observaciones en 5 días de misión distintos |
| Disponible desde | el día de misión del corte es 6 o posterior |
| Nombre del método | `experimental_fixed_window_mean_v1` |

- Hasta que el corte llega al día 6 la ventana aún puede recibir datos, así que
  la referencia no se declara aunque ya tenga 5 observaciones.
- Las observaciones posteriores al día 5 nunca actualizan la referencia.
- Si la ventana no tiene datos suficientes, el resultado es
  `insufficient_data`. La ventana nunca se amplía con días posteriores.
- Los días distintos se cuentan aparte de las observaciones: cinco lecturas en
  un mismo día son 5 observaciones en 1 día, y no alcanzan.

### Fórmulas

Para los valores `x1 … xn` de una serie:

- **Media:** `media = (x1 + … + xn) / n`
- **Desviación estándar poblacional:** `desv = sqrt(((x1 - media)² + … + (xn - media)²) / n)`.
  El denominador es `n`, no `n - 1`.
- **Mínimo, máximo y cantidad:** sobre los mismos valores.
- Sin valores, la cantidad es 0 y los demás estadísticos están ausentes (null),
  no valen 0.

Referencia: `referencia = media de los valores de la ventana`. `sample_count`
es el número de observaciones utilizadas.

Tendencia diaria, para cada día de misión con observaciones:

- `media_del_día = media de los valores de ese día`
- `delta = media_del_día - referencia`
- `cambio_porcentual = 100 * delta / referencia`, solo si la referencia no es 0

No hay regresión, suavizado, z-scores, predicciones ni umbrales. La media
diaria es un agregado interno. Nunca reemplaza los registros guardados ni
añade puntos a un historial.

### Ejemplos resueltos

**Referencia.** Frecuencia cardíaca en reposo, días 1-5: 76, 78, 80, 82, 84.
Suma 400, `400 / 5 = 80`. Referencia = 80 beats/min, 5 observaciones, 5 días.

**Tendencia.** El día 6 tiene dos lecturas en reposo, 86 y 90: media diaria
`(86 + 90) / 2 = 88`. `delta = 88 - 80 = 8`. `cambio_porcentual = 100 * 8 / 80 = 10`.
El día 7 tiene una lectura de 72: `delta = -8`, `cambio_porcentual = -10`.

**Desviación estándar.** Valores 2, 4, 4, 4, 5, 5, 7, 9: suma 40, media 5.
Las desviaciones al cuadrado 9, 1, 1, 1, 0, 0, 4, 16 suman 32. `32 / 8 = 4`,
`sqrt(4) = 2`.

**Semilla de demo.** `AST-001` tiene 72 beats/min, 98 %, 16 breaths/min y 7.5 h
en cada uno de los días 1-5, así que las referencias son 72, 98, 16 y 7.5 con
5 muestras cada una.

Los resultados no se redondean. Las pruebas comparan valores exactos cuando la
aritmética es exacta en binario y usan una tolerancia relativa de `1e-9` en el
resto.

### Datos ausentes, extremos y duplicados

- `null` significa ausencia y no participa en ningún cálculo. Un cero válido
  (por ejemplo 0 horas de sueño) es un valor y sí participa.
- Los valores inusuales pero bien formados se conservan. No se elimina ningún
  valor atípico.
- Un reenvío o una reimportación idéntica de una lectura no crea otra fila, así
  que no puede añadir peso. Dentro del análisis, un registro que aparece dos
  veces (mismo ID) también se cuenta una sola vez.
- Dos registros distintos con el mismo timestamp son dos observaciones. El
  almacenamiento ya impide dos lecturas de un astronauta con el mismo timestamp
  y contexto, y más de una entrada de diario por día. Los empates se ordenan
  por ID.
- Los timestamps se comparan de forma exacta, incluidos los dígitos por debajo
  del microsegundo.
- Ningún resultado es NaN ni infinito. Las entradas no finitas se rechazan.

### Referencia cero y varianza cero

- Si todos los valores son iguales, la desviación estándar es exactamente 0 y
  la media es exactamente ese valor. Nunca se divide por la desviación estándar.
- Una referencia de 0 es válida. `delta` se calcula; `cambio_porcentual` no
  está disponible, con el motivo `reference_is_zero`.
- Sin referencia, `delta` y `cambio_porcentual` no están disponibles, con el
  motivo `reference_unavailable`. El cero nunca se usa como sustituto.

### Corte y reproducibilidad

- Las observaciones se filtran por `as_of` antes de calcular cualquier
  referencia, estadístico, media diaria o tendencia. Nada posterior al corte
  puede afectar un resultado.
- Una ventana devuelta nunca termina después de `as_of`.
- Un corte dentro de un día usa solo lo observado hasta ese instante.
- Añadir observaciones posteriores no cambia el resultado de un corte anterior.
- Los resultados se calculan bajo demanda y no se guardan en caché, así que una
  escritura o importación nunca deja un análisis obsoleto.
- **Limitación:** `as_of` es un corte de observación, no un historial de
  versiones de la base de datos. Corregir una entrada del diario reemplaza los
  valores de ese día, por lo que el análisis de ese día, y una referencia que
  lo incluya, pueden cambiar. Lo mismo ocurre con una importación tardía cuyos
  timestamps caigan dentro de la ventana.

### Mapeo a `BaselineMetric`

`summary.baselines` conserva sus cuatro claves y sus campos actuales.

| Campo | `available` | `insufficient_data` |
| --- | --- | --- |
| `status` | `available` | `insufficient_data` |
| `value` | la media | null |
| `sample_count` | observaciones utilizadas | observaciones válidas de la ventana hasta el corte |
| `reference_start` | timestamp de la primera observación utilizada | null |
| `reference_end` | timestamp de la última observación utilizada | null |
| `measurement_context` | `rest` en vitales, null en sueño | igual |
| `method` | `experimental_fixed_window_mean_v1` | null |

Ya no se devuelve `not_implemented` en los baselines. El resumen de alertas y
`GET /alerts` siguen en `not_implemented` hasta #15.

### Diferencias respecto a los fixtures compartidos

Los fixtures son ejemplos contractuales ilustrativos y no se modificaron.

- Los baselines disponibles del fixture usan los límites de calendario de la
  ventana (`2026-11-01T00:00:00Z` a `2026-11-05T23:59:59Z`) y
  `method="fixture_reference_mean"`. La API informa las observaciones realmente
  utilizadas y su propio nombre de método. Estado, valor, cantidad de muestras
  y contexto coinciden.
- `summary_normal_reference_fixture` usa el corte `2026-11-05T23:59:59Z` y
  muestra `available`. Con la política provisional la referencia pasa a estar
  disponible en `2026-11-06T00:00:00Z`; un segundo antes la API devuelve
  `insufficient_data` con las mismas 5 muestras. El motor simulado del frontend
  sigue al fixture. Es la única diferencia material que el equipo debe resolver.

### Pendiente: exponer las tendencias por HTTP

El contrato no tiene campos HTTP para tendencias ni estadística descriptiva,
así que no se añadió ninguno ni se creó ningún endpoint. Propuesta mínima para
conversar con el responsable del frontend antes de cualquier cambio:

- Un endpoint de solo lectura, `GET /api/astronauts/{id}/trends`, con los
  parámetros existentes `as_of`, `from_day` y `to_day`.
- `data` con una clave por cada uno de los cuatro indicadores con referencia.
  Cada una contiene `unit`, `measurement_context` y una lista de puntos:
  `mission_day`, `daily_mean`, `sample_count`, `delta`, `percent_change` y
  `unavailable_reason` (`reference_unavailable`, `reference_is_zero` o null).
- `stats` opcional por indicador: `count`, `mean`, `minimum`, `maximum`,
  `population_std`.

Mientras no se acuerde, los gráficos ya pueden dibujar la línea de referencia
de `summary.baselines` sobre los historiales sin modificar.

### Límites

- Estadísticas de demostración sobre datos sintéticos; sin diagnóstico, sin
  validación clínica y sin umbrales médicos.
- Una única ventana fija por astronauta; sin referencia móvil ni adaptativa.
- El conjunto de demostración de 30 días (DATA-04) no es necesario y no se
  generó aquí.
