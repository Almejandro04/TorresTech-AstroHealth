# Health indicator dictionary / Diccionario de indicadores de salud

Issue: DATA-01 / #4. Structured version: [`indicator_dictionary.json`](indicator_dictionary.json).
Sources accessed 2026-11-15. Source codes (S1, S3, …) are listed at the end and in
[`../data_sources.md`](../data_sources.md).

- [English](#english)
- [Español](#español)

## English

### Purpose

An educational dictionary of the indicators AstroHealth displays, written for a
fictional-mission prototype. It is **not** a diagnostic system and it defines no
medical threshold. Field names, units and scales follow
[`docs/api_contract.md`](../api_contract.md) v0.1.0.

### Labels

| Label | Meaning |
| --- | --- |
| `[EVIDENCE-SPACEFLIGHT]` | Published evidence about spaceflight |
| `[TERRESTRIAL-CLINICAL]` | Terrestrial clinical reference (general adult population on Earth) |
| `[SIMULATION-ASSUMPTION]` | Assumption introduced only for the fictional mission |

### Dictionary

| field | Definition | Unit / scale | Context and sampling | Spaceflight relevance | References | Limitations | Baseline |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `heart_rate_bpm` | Heartbeats per minute in a point-in-time observation | beats/min; number > 0 | Compare only within the same `measurement_context`; the system baseline uses `rest` only. One resting reading per day at a similar time in the synthetic mission | [EVIDENCE-SPACEFLIGHT] Night-time HR unchanged on the ISS (S4); HR unchanged while cardiac output increased (S5); the challenge mentions cardiovascular events (S1). Real monitoring with Bio-Monitor (S14) | S1, S4, S5, S14; [TERRESTRIAL-CLINICAL] 60–100 in healthy adults (S15) | Changes with exercise, sleep, stress, medication and posture; 60–100 is a general terrestrial reference, not a threshold for astronauts; do not infer arrhythmias or diagnoses | `baseline_and_trend` (`rest` only) |
| `spo2_percent` | Peripheral oxygen saturation estimated by pulse oximetry | %; 0–100 | Same position and context; compare within the person | [EVIDENCE-SPACEFLIGHT] The 8.2 psia / 34% O2 exploration atmosphere introduces mild hypoxia (S8); in chamber tests there was no appreciable impact on SpO2 with mild exercise (S9) | S8, S9; [TERRESTRIAL-CLINICAL] 96–100% at rest (S16) | Sensor error, motion and perfusion; narrow range, small changes; not a diagnosis of hypoxia | `baseline_and_trend`, cautious interpretation (small variation) |
| `respiratory_rate_bpm` | Breaths per minute | breaths/min; number > 0 | Count at rest for 1 min (S15); do not mix with exercise or sleep | [EVIDENCE-SPACEFLIGHT] The breathing pattern changes in microgravity (more abdominal contribution; lower tidal volume) (S6, S7); an increase of ~9% appears in a review without a confirmed primary source (S7) | S6, S7; [TERRESTRIAL-CLINICAL] 12–16 (S15) or 12–20 (S16) | Terrestrial references differ between sources; device estimation varies; small samples in spaceflight studies | `baseline_and_trend` (`rest` only) |
| `sleep_hours_last_night` | Hours of sleep in the previous period, self-reported in the journal | hours; 0–24; 0 is a reported value | One entry per mission day; self-report | [EVIDENCE-SPACEFLIGHT] Mean in-flight sleep ~6.0 h (5.96 shuttle; 6.09 ISS) with 8.5 h scheduled (S3); stress and tiredness increase in the second half of 6-month missions (S12, preliminary) | S3, S12 | Self-report is less precise than actigraphy (S3 used both); does not measure sleep quality | `baseline_and_trend` |
| `mood_score` | Self-reported mood of the day | score; integer 1–5 (very low, low, neutral, high, very high) | Once a day in the journal; no preselected value | [EVIDENCE-SPACEFLIGHT] NASA BHP uses mood self-reports and the 37-item POMS as standard measures (S10); behavioral risk documented by HRP (S11) | S10, S11 | [SIMULATION-ASSUMPTION] The product's 1–5 scale is NOT the POMS nor a validated clinical scale; ordinal: do not average | `descriptive_only` |
| `perceived_fatigue` (optional, outside contract v0.1.0) | Self-reported perceived tiredness | Not defined in v0.1.0 | Documented only; not implemented | [EVIDENCE-SPACEFLIGHT] Tiredness appears in S12, and S3 mentions fatigue as a common complaint | S3, S12 | There is no contract field; it needs a team decision and a defined scale | Not applicable (out of scope) |

### Comparability and what must NOT be aggregated

- Do not combine readings from different contexts (`rest`, `exercise`, `sleep`,
  `unknown`) in one baseline or trend.
- Do not combine different astronauts, nor synthetic with terrestrial data.
- Do not average `mood_score` (ordinal) or present it as a clinical measure.
- Do not turn null into 0: a missing value is neither a normal nor an abnormal result.
- Do not compare against terrestrial ranges as if they were criteria for astronauts.
- Sleep (daily journal) and vitals (point-in-time readings) have different
  cadences: they are not merged into one series.
- Environmental data (S21) are not individual physiological measurements.

### What supports a baseline or trend

| field | Support | Note |
| --- | --- | --- |
| `heart_rate_bpm` | `baseline_and_trend` | `rest` readings only |
| `spo2_percent` | `baseline_and_trend` | Cautious interpretation: small variation |
| `respiratory_rate_bpm` | `baseline_and_trend` | `rest` readings only |
| `sleep_hours_last_night` | `baseline_and_trend` | Daily journal series |
| `mood_score` | `descriptive_only` | Ordinal; never averaged |
| `perceived_fatigue` | Not applicable | Outside contract v0.1.0 |

### Proposed experimental rules

The only implemented rule is `DEMO-HR-CHANGE` (+5 beats/min on 2 consecutive
days), and it is `[SIMULATION-ASSUMPTION]`: no source listed here supports that
threshold. See [`../architecture/alert_rules.md`](../architecture/alert_rules.md)
and [`../architecture/analysis.md`](../architecture/analysis.md).

## Español

### Propósito

Diccionario educativo de los indicadores que muestra AstroHealth, escrito para
un prototipo con una misión ficticia. **No** es un sistema diagnóstico y no
define ningún umbral médico. Los nombres de campo, unidades y escalas siguen
[`docs/api_contract.md`](../api_contract.md) v0.1.0.

### Etiquetas

| Etiqueta | Significado |
| --- | --- |
| `[EVIDENCE-SPACEFLIGHT]` | Evidencia publicada sobre vuelo espacial |
| `[TERRESTRIAL-CLINICAL]` | Referencia clínica terrestre (población adulta general en la Tierra) |
| `[SIMULATION-ASSUMPTION]` | Supuesto introducido solo para la misión ficticia |

### Diccionario

| field | Definición | Unidad / escala | Contexto y muestreo | Relevancia en vuelo | Referencias | Limitaciones | Baseline |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `heart_rate_bpm` | Latidos del corazón por minuto en una observación puntual | beats/min; número > 0 | Comparar solo dentro del mismo `measurement_context`; el baseline del sistema usa solo `rest`. Una lectura por día en reposo a hora similar en la misión sintética | [EVIDENCE-SPACEFLIGHT] FC nocturna sin cambio en la ISS (S4); FC sin cambio con aumento de gasto cardíaco (S5); el reto menciona eventos cardiovasculares (S1). Monitoreo real con Bio-Monitor (S14) | S1, S4, S5, S14; [TERRESTRIAL-CLINICAL] 60–100 en adultos sanos (S15) | Cambia con ejercicio, sueño, estrés, medicación y postura; 60–100 es referencia terrestre general, no umbral para astronautas; no inferir arritmias ni diagnósticos | `baseline_and_trend` (solo `rest`) |
| `spo2_percent` | Saturación periférica de oxígeno estimada por pulsioximetría | %; 0–100 | Misma posición y contexto; comparar dentro de la persona | [EVIDENCE-SPACEFLIGHT] la atmósfera de exploración 8.2 psia / 34% O2 introduce hipoxia leve (S8); en pruebas en cámara no hubo impacto apreciable en SpO2 con ejercicio leve (S9) | S8, S9; [TERRESTRIAL-CLINICAL] 96–100% en reposo (S16) | Error del sensor, movimiento y perfusión; rango estrecho, cambios pequeños; no es diagnóstico de hipoxia | `baseline_and_trend` con interpretación cautelosa (variación pequeña) |
| `respiratory_rate_bpm` | Respiraciones por minuto | breaths/min; número > 0 | Contar en reposo durante 1 min (S15); no mezclar con ejercicio o sueño | [EVIDENCE-SPACEFLIGHT] el patrón respiratorio cambia en microgravedad (más contribución abdominal; menor volumen corriente) (S6, S7); un aumento de ~9% aparece en una revisión sin fuente primaria confirmada (S7) | S6, S7; [TERRESTRIAL-CLINICAL] 12–16 (S15) o 12–20 (S16) | Las referencias terrestres difieren entre fuentes; la estimación por dispositivo varía; muestra pequeña en estudios de vuelo | `baseline_and_trend` (solo `rest`) |
| `sleep_hours_last_night` | Horas de sueño del periodo previo, autoinformadas en el diario | hours; 0–24; 0 es un valor informado | Una entrada por día de misión; autoinforme | [EVIDENCE-SPACEFLIGHT] sueño medio en vuelo ~6.0 h (5.96 shuttle; 6.09 ISS) con 8.5 h programadas (S3); estrés y cansancio aumentan en la segunda mitad de misiones de 6 meses (S12, preliminar) | S3, S12 | Autoinforme menos preciso que actigrafía (S3 usó ambos); no mide calidad del sueño | `baseline_and_trend` |
| `mood_score` | Estado de ánimo autoinformado del día | score; entero 1–5 (very low, low, neutral, high, very high) | Una vez al día en el diario; sin valor preseleccionado | [EVIDENCE-SPACEFLIGHT] NASA BHP usa autoinformes de ánimo y el POMS de 37 ítems como medidas estándar (S10); riesgo conductual documentado por HRP (S11) | S10, S11 | [SIMULATION-ASSUMPTION] escala 1–5 del producto, NO es el POMS ni una escala clínica validada; ordinal: no promediar | `descriptive_only` |
| `perceived_fatigue` (opcional, fuera del contrato v0.1.0) | Cansancio percibido autoinformado | No definido en v0.1.0 | Solo documentado; no implementar | [EVIDENCE-SPACEFLIGHT] el cansancio aparece en S12 y S3 menciona la fatiga como queja común | S3, S12 | No hay campo en el contrato; requiere decisión de equipo y escala definida | No aplica (fuera de alcance) |

### Comparabilidad y lo que NO debe agregarse

- No combinar lecturas de contextos distintos (`rest`, `exercise`, `sleep`,
  `unknown`) en un mismo baseline ni tendencia.
- No combinar astronautas distintos ni datos sintéticos con terrestres.
- No promediar `mood_score` (ordinal) ni presentarlo como medida clínica.
- No convertir null en 0: la ausencia de dato no es resultado normal ni anormal.
- No comparar contra rangos terrestres como si fueran criterios para astronautas.
- El sueño (diario) y los vitales (lecturas puntuales) tienen cadencias
  distintas: no se mezclan en una sola serie.
- Los datos ambientales (S21) no son mediciones fisiológicas individuales.

### Qué soporta baseline o tendencia

| field | Soporte | Nota |
| --- | --- | --- |
| `heart_rate_bpm` | `baseline_and_trend` | Solo lecturas `rest` |
| `spo2_percent` | `baseline_and_trend` | Interpretación cautelosa: variación pequeña |
| `respiratory_rate_bpm` | `baseline_and_trend` | Solo lecturas `rest` |
| `sleep_hours_last_night` | `baseline_and_trend` | Serie diaria del diario |
| `mood_score` | `descriptive_only` | Ordinal; nunca se promedia |
| `perceived_fatigue` | No aplica | Fuera del contrato v0.1.0 |

### Reglas experimentales propuestas

La única regla implementada es `DEMO-HR-CHANGE` (+5 beats/min en 2 días
consecutivos) y es `[SIMULATION-ASSUMPTION]`: ninguna de las fuentes listadas
respalda ese umbral. Consulta
[`../architecture/alert_rules.md`](../architecture/alert_rules.md) y
[`../architecture/analysis.md`](../architecture/analysis.md).

## Sources / Fuentes (accessed / acceso 2026-11-15)

- **S1** NASA Space Apps Challenge 2026 — "Create Health Monitoring Software for Astronauts on Space Missions". https://www.spaceappschallenge.org/2026/challenges/
- **S3** Barger LK, Flynn-Evans EE, Kubey A, Walsh L, Ronda JM, Wang W, Wright KP, Czeisler CA. Prevalence of sleep deficiency and use of hypnotic drugs in astronauts before, during, and after spaceflight: an observational study. Lancet Neurol. 2014;13(9):904–912. DOI 10.1016/S1474-4422(14)70122-X. PMCID PMC4188436.
- **S4** CSA — CCISS (Cardiovascular and Cerebrovascular Control on return from ISS), PI Richard L. Hughson. https://asc-csa.gc.ca/eng/sciences/cciss.asp ; IAC-11 abstract (Fraser KS et al., 2011): https://iafastro.directory/iac/archive/browse/IAC-11/A1/2/9471/ (conference abstract, not a full article).
- **S5** Norsk P, Asmar A, Damgaard M, Christensen NJ. Fluid shifts, vasodilatation and ambulatory blood pressure reduction during long duration spaceflight. J Physiol 2015. PMCID PMC4324706. https://pmc.ncbi.nlm.nih.gov/articles/PMC4324706/
- **S6** Prisk GK. Pulmonary challenges of prolonged journeys to space: taking your lungs to the moon. Med J Aust. 2019;211(6):271–276. DOI 10.5694/mja2.50312. PMCID PMC6745695.
- **S7** Smith MB, Chen H, Oliver BGG. The Lungs in Space: A Review of Current Knowledge and Methodologies. Cells 2024;13(13):1154. DOI 10.3390/cells13131154. The 9% respiratory-rate increase is secondary data; primary source not confirmed.
- **S8** Norcross JR, Conkin J, Wessel JH, Norsk P, et al. Evidence Report: Risk of Hypobaric Hypoxia from the Exploration Atmosphere. NASA HRP. NTRS 20150021491. https://ntrs.nasa.gov/citations/20150021491
- **S9** NASA NTRS 20230015594 — Effects of Mild Hypobaric Hypoxia on Response From Mild Exercise in NASA Exploration Atmosphere Tests. https://ntrs.nasa.gov/citations/20230015594 (ground chamber study).
- **S10** NASA HRP — Behavioral Health and Performance Standard Measures. NTRS 20190000670: https://ntrs.nasa.gov/citations/20190000670 ; NTRS 20170005421: https://ntrs.nasa.gov/api/citations/20170005421/downloads/20170005421.pdf
- **S11** NASA HRP — Evidence Report: Risk of Adverse Cognitive or Behavioral Conditions and Psychiatric Disorders (BMed). NTRS 20150016966: https://ntrs.nasa.gov/api/citations/20150016966/downloads/20150016966.pdf ; current version (2025): https://ntrs.nasa.gov/api/citations/20250001454/downloads/BMed%20Evidence%20Report%20final%202-10-25.docx
- **S12** Dinges DF, Basner M, et al. Effects of Time in Mission: ISS Astronauts Ratings of Stress (abstract; Reaction Self Test). https://typeset.io/pdf/effects-of-time-in-mission-iss-astronauts-ratings-of-stress-3x0ck6kyq9.pdf (preliminary conference result).
- **S14** CSA — Bio-Monitor. https://asc-csa.gc.ca/eng/sciences/astroskin.asp
- **S15** Johns Hopkins Medicine — Vital Signs. https://www.hopkinsmedicine.org/health/conditions-and-diseases/vital-signs-body-temperature-pulse-rate-respiration-rate-blood-pressure
- **S16** Michigan Medicine (Healthwise) — Normal Vital Signs for Adults. https://www.uofmhealth.org/health-library/acp1895 (current as of 2024-07-31).
- **S21** NASA OSDR — Environmental Data App (EDA). https://visualization.osdr.nasa.gov/eda ; NTRS 20240008072: https://ntrs.nasa.gov/citations/20240008072
