# Data sources and citations / Fuentes de datos y citas

Issue: DATA-05 / #19. Accessed / acceso: 2026-11-15.

Related: [health_indicators.md](research/health_indicators.md) ·
[indicator_dictionary.json](research/indicator_dictionary.json) ·
[dataset_candidates.md](research/dataset_candidates.md) ·
[data/README.md](../data/README.md) · [data/synthetic/README.md](../data/synthetic/README.md) ·
[analysis.md](architecture/analysis.md) · [alert_rules.md](architecture/alert_rules.md) ·
[validation_review.md](research/validation_review.md) ·
[sources_manifest.json](../data/sources/sources_manifest.json)

Labels: `[EVIDENCE-SPACEFLIGHT]` published spaceflight evidence ·
`[TERRESTRIAL-CLINICAL]` terrestrial clinical reference ·
`[SIMULATION-ASSUMPTION]` assumption introduced only for the fictional mission.

- [English](#english)
- [Español](#español)

## English

### Source → files

| source_id | Files | Status |
| --- | --- | --- |
| `SYN-AH-MISSION-001` | `data/synthetic/*` | Generated, committed |
| `PHYSIONET-BIDMC-1.0.0` | `data/processed/bidmc_subset/*` (raw downloads in `data/raw/`, git-ignored) | Processed subset committed |
| `SYN-CORE-001` | `docs/examples/mission_seed.json` | Contract fixture, unchanged |

### Datasets

**SYN-AH-MISSION-001 — synthetic 30-day mission** `[SIMULATION-ASSUMPTION]`
- Version: generator 1.0.0, seed 2026, start date 2026-11-01; contract schema 0.1.0.
- URL: none (generated locally by `data/scripts/generate_synthetic_mission.py`).
- License / conditions: project data; no third-party data included.
- Population: fictional astronauts AST-101 (30 days), AST-102 (days 1–3) and AST-201..205 fixtures.
- Variables and units: `heart_rate_bpm` (beats/min), `spo2_percent` (%), `respiratory_rate_bpm`
  (breaths/min), `sleep_hours_last_night` (hours), `mood_score` (1–5).
- Context: `rest` daily at 12:00Z; `sleep` (03:00Z) and `exercise` (17:00Z) on even days.
- Timestamps: UTC with `Z`; `mission_day` from the start date. Journal at 08:00Z.
- Missing values: explicit null (day 12 HR, day 13 RR) and absent journal (day 14); never 0.
- Normalization / resampling: none; values are generated directly in contract units.

**PHYSIONET-BIDMC-1.0.0 — BIDMC PPG and Respiration Dataset** `[TERRESTRIAL-CLINICAL]`
- Version 1.0.0, DOI 10.13026/C2208R. URL: https://physionet.org/content/bidmc/1.0.0/
- License: Open Data Commons Attribution License v1.0 (ODC-By), open access.
- Citations: S17, S18, S19 (below).
- Population: terrestrial critically ill patients, Beth Israel Deaconess Medical Center
  (Boston), from the MIMIC II matched waveform database. Subset: `bidmc_01`–`bidmc_03`.
- Variables and units: HR → `heart_rate_bpm` (beats/min), PULSE → `pulse_rate_bpm`,
  RESP → `respiratory_rate_bpm` (breaths/min), SpO2 → `spo2_percent` (%), 1 Hz numerics.
- Context: `unknown` (ICU bedside monitor, non-standardized situation).
- Timestamps: elapsed seconds only; no UTC timestamps or mission days (source dates are
  shifted by de-identification and are not real).
- Missing values: NaN → null; shape failures → null and counted; empty rows rejected.
- Normalization / resampling: 60 s windows, median per variable, null below 30 valid
  seconds. Details in [data/README.md](../data/README.md).
- Never loaded into astronaut routes and never relabeled as astronaut data.

**SYN-CORE-001 — CORE-01 contract fixtures** `[SIMULATION-ASSUMPTION]`
- Seven days for AST-001 and AST-002 in `docs/examples/mission_seed.json`; same units,
  contexts and timestamp policy as the contract. Unchanged by these tasks.

### Research references (not datasets)

| Code | Reference | Category |
| --- | --- | --- |
| S1 | NASA Space Apps Challenge 2026 — "Create Health Monitoring Software for Astronauts on Space Missions". https://www.spaceappschallenge.org/2026/challenges/ | Challenge statement |
| S2 | Space Apps 2026 participant terms. https://www.spaceappschallenge.org/legal/ | Citation requirement |
| S3 | Barger LK et al. Lancet Neurol. 2014;13(9):904–912. DOI 10.1016/S1474-4422(14)70122-X. PMCID PMC4188436 | `[EVIDENCE-SPACEFLIGHT]` |
| S4 | CSA — CCISS, PI Richard L. Hughson. https://asc-csa.gc.ca/eng/sciences/cciss.asp ; IAC-11 abstract (Fraser KS et al., 2011) https://iafastro.directory/iac/archive/browse/IAC-11/A1/2/9471/ | `[EVIDENCE-SPACEFLIGHT]` (conference abstract) |
| S5 | Norsk P, Asmar A, Damgaard M, Christensen NJ. J Physiol 2015. PMCID PMC4324706 | `[EVIDENCE-SPACEFLIGHT]` |
| S6 | Prisk GK. Med J Aust. 2019;211(6):271–276. DOI 10.5694/mja2.50312. PMCID PMC6745695 | `[EVIDENCE-SPACEFLIGHT]` |
| S7 | Smith MB, Chen H, Oliver BGG. Cells 2024;13(13):1154. DOI 10.3390/cells13131154 | `[EVIDENCE-SPACEFLIGHT]` (review; the 9% RR increase is secondary, primary source not confirmed) |
| S8 | Norcross JR, Conkin J, Wessel JH, Norsk P, et al. NASA HRP Evidence Report, NTRS 20150021491. https://ntrs.nasa.gov/citations/20150021491 | `[EVIDENCE-SPACEFLIGHT]` |
| S9 | NASA NTRS 20230015594. https://ntrs.nasa.gov/citations/20230015594 | `[EVIDENCE-SPACEFLIGHT]` (ground chamber study) |
| S10 | NASA HRP BHP Standard Measures. NTRS 20190000670; NTRS 20170005421 | `[EVIDENCE-SPACEFLIGHT]` |
| S11 | NASA HRP BMed Evidence Report. NTRS 20150016966; 2025 version NTRS 20250001454 | `[EVIDENCE-SPACEFLIGHT]` |
| S12 | Dinges DF, Basner M, et al. Effects of Time in Mission: ISS Astronauts Ratings of Stress. https://typeset.io/pdf/effects-of-time-in-mission-iss-astronauts-ratings-of-stress-3x0ck6kyq9.pdf | `[EVIDENCE-SPACEFLIGHT]` (preliminary conference result) |
| S13 | NASA-STD-3001 Technical Briefs (OCHMO). https://www.nasa.gov/ochmo/health-operations-and-oversight/hsa-standards/ | Reference only; defines no project threshold |
| S14 | CSA — Bio-Monitor. https://asc-csa.gc.ca/eng/sciences/astroskin.asp | `[EVIDENCE-SPACEFLIGHT]` (monitoring example) |
| S15 | Johns Hopkins Medicine — Vital Signs. https://www.hopkinsmedicine.org/health/conditions-and-diseases/vital-signs-body-temperature-pulse-rate-respiration-rate-blood-pressure | `[TERRESTRIAL-CLINICAL]` |
| S16 | Michigan Medicine (Healthwise) — Normal Vital Signs for Adults. https://www.uofmhealth.org/health-library/acp1895 | `[TERRESTRIAL-CLINICAL]` |
| S21 | NASA OSDR — Environmental Data App. https://visualization.osdr.nasa.gov/eda ; NTRS 20240008072 | Environmental, not physiological |
| S22 | Sanders LM et al. npj Microgravity 2024;10:56. DOI 10.1038/s41526-024-00393-5. PMCID PMC11094041 | `[EVIDENCE-SPACEFLIGHT]` (omics; context only) |
| S23 | NASA LSDA / LSAH data request. https://nlsp.nasa.gov/explore/lsdahome/datarequest | Access by request (IRB) |
| S24 | NASA OSDR terms and citation. https://science.nasa.gov/reference/osdr-help-terms-and-conditions | Terms |
| S25 | NASA HRP. https://www.nasa.gov/hrp/ | Program portal |

Dataset citations: **S17** PhysioNet BIDMC v1.0.0, https://physionet.org/content/bidmc/1.0.0/,
DOI 10.13026/C2208R. **S18** Pimentel MAF et al. IEEE Trans Biomed Eng. 2016;64(8):1914–1923.
DOI 10.1109/TBME.2016.2613124. **S19** Pollard T, Moody BE, Lehman L, Gow B, Fernandes C,
Xie C, Johnson A, Mark RG, Heldt T. PhysioNet as a global platform for biomedical research.
Nature Health (2026). DOI 10.1038/s44360-026-00096-z. **S20** (candidate, rejected) WESAD,
UCI id 465, DOI 10.24432/C57K5T, Schmidt P, Reiss A (2018).

### Limits of transferring terrestrial observations

- BIDMC subjects are critically ill ICU patients; they do not represent healthy astronauts.
- Terrestrial clinical ranges (S15, S16) are not spaceflight criteria.
- The synthetic mission does not reproduce validated spaceflight physiology.
- There is no access to astronaut health records within this project (S23).

### NASA Space Apps citation

Space Apps requires citing every resource used, including open-source ones (S2). Resources:
S1–S25 above; PhysioNet BIDMC (S17–S19); the project's own synthetic data; open-source
software listed in `backend/requirements.txt` and `frontend/package.json`. AI tools used by
the team: **Claude Code** (Anthropic) to implement code and documentation, and **Codex**
(OpenAI) to review changes. AI output was reviewed by the team.

## Español

### Fuente → archivos

| source_id | Archivos | Estado |
| --- | --- | --- |
| `SYN-AH-MISSION-001` | `data/synthetic/*` | Generado, versionado |
| `PHYSIONET-BIDMC-1.0.0` | `data/processed/bidmc_subset/*` (descargas crudas en `data/raw/`, ignorado por git) | Subconjunto procesado versionado |
| `SYN-CORE-001` | `docs/examples/mission_seed.json` | Fixture del contrato, sin cambios |

### Datasets

**SYN-AH-MISSION-001 — misión sintética de 30 días** `[SIMULATION-ASSUMPTION]`
- Versión: generador 1.0.0, semilla 2026, fecha de inicio 2026-11-01; esquema del contrato 0.1.0.
- URL: ninguna (generado localmente por `data/scripts/generate_synthetic_mission.py`).
- Licencia / condiciones: datos del proyecto; no incluye datos de terceros.
- Población: astronautas ficticios AST-101 (30 días), AST-102 (días 1–3) y fixtures AST-201..205.
- Variables y unidades: `heart_rate_bpm` (beats/min), `spo2_percent` (%), `respiratory_rate_bpm`
  (breaths/min), `sleep_hours_last_night` (hours), `mood_score` (1–5).
- Contexto: `rest` diario a las 12:00Z; `sleep` (03:00Z) y `exercise` (17:00Z) en días pares.
- Timestamps: UTC con `Z`; `mission_day` desde la fecha de inicio. Diario a las 08:00Z.
- Faltantes: null explícito (FC día 12, FR día 13) y diario ausente (día 14); nunca 0.
- Normalización / remuestreo: ninguno; los valores se generan directamente en unidades del contrato.

**PHYSIONET-BIDMC-1.0.0 — BIDMC PPG and Respiration Dataset** `[TERRESTRIAL-CLINICAL]`
- Versión 1.0.0, DOI 10.13026/C2208R. URL: https://physionet.org/content/bidmc/1.0.0/
- Licencia: Open Data Commons Attribution License v1.0 (ODC-By), acceso abierto.
- Citas: S17, S18, S19 (arriba).
- Población: pacientes críticos terrestres, Beth Israel Deaconess Medical Center (Boston),
  de MIMIC II matched waveform database. Subconjunto: `bidmc_01`–`bidmc_03`.
- Variables y unidades: HR → `heart_rate_bpm` (beats/min), PULSE → `pulse_rate_bpm`,
  RESP → `respiratory_rate_bpm` (breaths/min), SpO2 → `spo2_percent` (%), numerics a 1 Hz.
- Contexto: `unknown` (monitor de cabecera en UCI, situación no estandarizada).
- Timestamps: solo segundos transcurridos; sin timestamps UTC ni días de misión (las fechas
  de la fuente están desplazadas por desidentificación y no son reales).
- Faltantes: NaN → null; fallos de forma → null y contados; filas vacías rechazadas.
- Normalización / remuestreo: ventanas de 60 s, mediana por variable, null con menos de 30
  segundos válidos. Detalles en [data/README.md](../data/README.md).
- Nunca se carga en las rutas de astronautas ni se etiqueta como dato de astronauta.

**SYN-CORE-001 — fixtures del contrato CORE-01** `[SIMULATION-ASSUMPTION]`
- Siete días para AST-001 y AST-002 en `docs/examples/mission_seed.json`; mismas unidades,
  contextos y política de timestamps que el contrato. Sin cambios en estas tareas.

### Referencias de investigación (no son datasets)

La tabla de la sección en inglés lista S1–S16 y S21–S25 con su categoría; las citas de
datasets S17–S20 están debajo de ella.

### Límites al transferir observaciones terrestres

- Los sujetos de BIDMC son pacientes críticos en UCI; no representan astronautas sanos.
- Los rangos clínicos terrestres (S15, S16) no son criterios de vuelo.
- La misión sintética no reproduce fisiología espacial validada.
- No hay acceso a registros de salud de astronautas en este proyecto (S23).

### Cita para NASA Space Apps

Space Apps exige citar todos los recursos usados, incluidos los open source (S2). Recursos:
S1–S25; PhysioNet BIDMC (S17–S19); los datos sintéticos propios; el software open source de
`backend/requirements.txt` y `frontend/package.json`. Herramientas de IA usadas por el
equipo: **Claude Code** (Anthropic) para implementar código y documentación, y **Codex**
(OpenAI) para revisar cambios. El equipo revisó lo producido por la IA.
