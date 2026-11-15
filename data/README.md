# AstroHealth data / Datos de AstroHealth

- [English](#english)
- [Español](#español)

## English

| Folder | Content | Committed |
| --- | --- | --- |
| `sources/` | `sources_manifest.json`: every data source used | yes |
| `raw/` | Downloaded BIDMC files | **no** (git-ignored) |
| `processed/bidmc_subset/` | Normalized 1-minute BIDMC subset, manifest, quality report | yes |
| `scripts/` | Acquisition, normalization and synthetic-mission scripts | yes |
| `tests/` | Offline tests (no network) | yes |

### Terrestrial subset: PhysioNet BIDMC v1.0.0 (DATA-03)

From the repository root:

```powershell
.\.venv\Scripts\python.exe data\scripts\acquire_bidmc.py
.\.venv\Scripts\python.exe data\scripts\normalize_bidmc.py
```

- `acquire_bidmc.py` downloads only `bidmc_01`, `bidmc_02` and `bidmc_03`
  (`_Numerics.csv`, `_Fix.txt`) and `SHA256SUMS.txt` to `data/raw/bidmc/`, checks
  every file against the official checksums, and writes `acquisition.json`. Use
  `--subjects 04 05` to choose others. Without network it exits with a non-zero code.
- `normalize_bidmc.py` writes `data/processed/bidmc_subset/`:
  `numerics_1min.csv`, `manifest.json`, `quality_report.json`.
- Mapping: `Time [s]` → `elapsed_s`, `HR` → `heart_rate_bpm`,
  `PULSE` → `pulse_rate_bpm`, `RESP` → `respiratory_rate_bpm`, `SpO2` → `spo2_percent`.
- Identity: `subject_id = "bidmc:##"`, `source_type = "terrestrial_biomedical"`,
  `source_id = "PHYSIONET-BIDMC-1.0.0"`, `measurement_context = "unknown"` (an ICU
  bedside monitor in a non-standardized situation, not a protocol resting measurement).
- Timebase: elapsed seconds only. No UTC timestamp or mission day is created; the
  source dates are shifted by de-identification (year 2688) and are not real.
- Quality: duplicate seconds are dropped (first kept); HR, PULSE or RESP <= 0 and
  SpO2 outside 0-100 become null as shape failures (not clinical outliers); rows with
  no values are rejected. All are counted in `quality_report.json`.
- Resampling: 60 s windows per subject with the **median** of each variable and its
  number of valid seconds (`n_valid_*`). With fewer than 30 valid seconds the variable
  is null in that window. The last partial window of each recording is kept, so its
  values are usually null.
- These are terrestrial ICU patients `[TERRESTRIAL-CLINICAL]`. They are never loaded
  into the astronaut API and never mixed into the synthetic mission.

**Attribution (ODC-By v1.0).** Contains data from the PhysioNet BIDMC PPG and
Respiration Dataset v1.0.0 (DOI 10.13026/C2208R), licensed under the Open Data
Commons Attribution License v1.0. Cite: Pimentel MAF et al., IEEE Trans Biomed Eng
2016;64(8):1914–1923, DOI 10.1109/TBME.2016.2613124; and Pollard T et al.,
PhysioNet as a global platform for biomedical research, Nature Health (2026),
DOI 10.1038/s44360-026-00096-z.

### Tests

```powershell
.\.venv\Scripts\python.exe -m pytest data\tests -q
```

## Español

| Carpeta | Contenido | Se versiona |
| --- | --- | --- |
| `sources/` | `sources_manifest.json`: todas las fuentes de datos usadas | sí |
| `raw/` | Archivos BIDMC descargados | **no** (ignorado por git) |
| `processed/bidmc_subset/` | Subconjunto BIDMC normalizado a 1 minuto, manifiesto, reporte de calidad | sí |
| `scripts/` | Scripts de adquisición, normalización y misión sintética | sí |
| `tests/` | Pruebas sin red | sí |

### Subconjunto terrestre: PhysioNet BIDMC v1.0.0 (DATA-03)

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe data\scripts\acquire_bidmc.py
.\.venv\Scripts\python.exe data\scripts\normalize_bidmc.py
```

- `acquire_bidmc.py` descarga solo `bidmc_01`, `bidmc_02` y `bidmc_03`
  (`_Numerics.csv`, `_Fix.txt`) y `SHA256SUMS.txt` a `data/raw/bidmc/`, verifica cada
  archivo con los checksums oficiales y escribe `acquisition.json`. Usa
  `--subjects 04 05` para elegir otros. Sin red termina con código distinto de cero.
- `normalize_bidmc.py` escribe `data/processed/bidmc_subset/`:
  `numerics_1min.csv`, `manifest.json`, `quality_report.json`.
- Mapeo: `Time [s]` → `elapsed_s`, `HR` → `heart_rate_bpm`,
  `PULSE` → `pulse_rate_bpm`, `RESP` → `respiratory_rate_bpm`, `SpO2` → `spo2_percent`.
- Identidad: `subject_id = "bidmc:##"`, `source_type = "terrestrial_biomedical"`,
  `source_id = "PHYSIONET-BIDMC-1.0.0"`, `measurement_context = "unknown"` (monitor de
  cabecera en UCI en una situación no estandarizada, no una medición en reposo de
  protocolo).
- Base temporal: solo segundos transcurridos. No se crean timestamps UTC ni días de
  misión; las fechas de la fuente están desplazadas por desidentificación (año 2688) y
  no son reales.
- Calidad: los segundos duplicados se descartan (se conserva el primero); HR, PULSE o
  RESP <= 0 y SpO2 fuera de 0-100 pasan a null como fallos de forma (no son outliers
  clínicos); las filas sin valores se rechazan. Todo se cuenta en `quality_report.json`.
- Remuestreo: ventanas de 60 s por sujeto con la **mediana** de cada variable y su
  número de segundos válidos (`n_valid_*`). Con menos de 30 segundos válidos la variable
  es null en esa ventana. Se conserva la última ventana parcial de cada grabación, por
  lo que sus valores suelen ser null.
- Son pacientes terrestres de UCI `[TERRESTRIAL-CLINICAL]`. Nunca se cargan en la API
  de astronautas ni se mezclan en la misión sintética.

**Atribución (ODC-By v1.0).** Contiene datos del PhysioNet BIDMC PPG and Respiration
Dataset v1.0.0 (DOI 10.13026/C2208R), con licencia Open Data Commons Attribution
License v1.0. Citar: Pimentel MAF et al., IEEE Trans Biomed Eng 2016;64(8):1914–1923,
DOI 10.1109/TBME.2016.2613124; y Pollard T et al., PhysioNet as a global platform for
biomedical research, Nature Health (2026), DOI 10.1038/s44360-026-00096-z.

### Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest data\tests -q
```
