# Dataset candidates / Candidatos de datasets

Issue: DATA-02 / #5. Accessed / acceso: 2026-11-15.
Manifest: [`data/sources/sources_manifest.json`](../../data/sources/sources_manifest.json).
Labels as in [`health_indicators.md`](health_indicators.md).

- [English](#english)
- [Español](#español)

## English

### Candidates

| Candidate | Type | Population | Variables | Format / size | Access / license | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| PhysioNet BIDMC v1.0.0 (S17) | Downloadable dataset | Terrestrial humans: critically ill patients at Beth Israel Deaconess Medical Center (Boston), derived from the MIMIC II matched waveform database; 53 recordings of ~8 min | Numerics at 1 Hz: HR (ECG), PULSE (PPG), RESP (impedance, by the monitor), SpO2 (%); signals at 125 Hz (PPG, impedance respiration, ECG); age and sex in `*_Fix.txt` | CSV, WFDB and MATLAB; 207.7 MB uncompressed; ZIP https://physionet.org/content/bidmc/get-zip/1.0.0/ | Open; ODC-By v1.0; cite S18 and S19 | **SELECTED** for DATA-03 (small subset of numerics) |
| WESAD, UCI id 465 (S20) | Downloadable dataset | 15 lab subjects; neutral, stress and amusement states | RespiBAN (chest, 700 Hz): ECG, EDA, EMG, respiration, temperature, acceleration; Empatica E4 (wrist): BVP 64 Hz, EDA 4 Hz, temperature 4 Hz, acceleration 32 Hz | Format described in its readme; the page gives no size in bytes | The UCI page does not state the license: not verified | **REJECTED**: no SpO2 and no direct HR (it would have to be derived from ECG/BVP), license not verified, large volume |
| NASA OSDR — Inspiration4 (S22) | Repository with open datasets | 4 civilian astronauts, 3-day mission | Omics and blood panels (OSD-569, -570, -571, -575) | Various | Open (OSDR) | **REJECTED** for the pipeline: no HR, SpO2, RR, sleep or mood series. Cited as context for real human spaceflight data |
| NASA OSDR — Environmental Data App (S21) | Tool with downloadable tables | ISS cabin and ground control; Rodent Research missions | Temperature, CO2, relative humidity, radiation dose | Downloadable tables | Public | **REJECTED** for vitals: environmental, not physiological data. Possible future extension as environmental context |
| NASA LSDA / LSAH (S23) | Archive with access on request | Astronauts and analog subjects | Clinical and research data | Not applicable | Requires review, approval and NASA IRB | **REJECTED**: not accessible within the project time |
| NASA HRP (S25) and NASA-STD-3001 (S13) | Evidence portals, not datasets | — | — | — | — | Evidence sources, not data sources |

### Selected source: PhysioNet BIDMC v1.0.0

- DOI 10.13026/C2208R. License: Open Data Commons Attribution License v1.0
  (ODC-By), open access. Required citations: S17, S18, S19.
- Per-subject files (`##` = 01..53): `bidmc_##_Numerics.csv`, `bidmc_##_Signals.csv`,
  `bidmc_##_Breaths.csv`, `bidmc_##_Fix.txt`. Root files: `README`, `LICENSE`,
  `RECORDS`, `SHA256SUMS.txt`, `ANNOTATORS`, `DBS`.
- File URLs: `https://physionet.org/files/bidmc/1.0.0/bidmc_csv/bidmc_##_Numerics.csv`
  and `https://physionet.org/files/bidmc/1.0.0/bidmc_csv/bidmc_##_Fix.txt`.
  Official checksums: https://physionet.org/files/bidmc/1.0.0/SHA256SUMS.txt
- Exact Numerics header (a space after each comma): `Time [s], HR, PULSE, RESP, SpO2`.
- `bidmc_01_Numerics.csv`: 481 data rows (Time 0..480 s, no gaps); NaN in PULSE and
  SpO2 between Time 111 and 123. First row: 0, 94, 93, 25, 97.
- `bidmc_01_Fix.txt` describes an 88-year-old male patient in the MICU, MIMIC II
  identifier s01182, and a date-shifted segment (year 2688) from de-identification:
  those dates are NOT real and must NOT be turned into UTC timestamps.
- Selected subjects: `bidmc_01`, `bidmc_02`, `bidmc_03` (Numerics and Fix only).
- These are terrestrial ICU patients `[TERRESTRIAL-CLINICAL]`. They are never
  relabeled as astronauts and never loaded into the astronaut API.

## Español

### Candidatos

| Candidato | Tipo | Población | Variables | Formato / tamaño | Acceso / licencia | Decisión |
| --- | --- | --- | --- | --- | --- | --- |
| PhysioNet BIDMC v1.0.0 (S17) | Dataset descargable | Humanos terrestres: pacientes críticos en el Beth Israel Deaconess Medical Center (Boston), derivado de MIMIC II matched waveform database; 53 grabaciones de ~8 min | Numerics a 1 Hz: HR (ECG), PULSE (PPG), RESP (impedancia, por el monitor), SpO2 (%); señales a 125 Hz (PPG, respiración por impedancia, ECG); edad y sexo en `*_Fix.txt` | CSV, WFDB y MATLAB; 207.7 MB sin comprimir; ZIP https://physionet.org/content/bidmc/get-zip/1.0.0/ | Abierto; ODC-By v1.0; citar S18 y S19 | **SELECCIONADO** para DATA-03 (subconjunto pequeño de numerics) |
| WESAD, UCI id 465 (S20) | Dataset descargable | 15 sujetos en laboratorio; estados neutral, estrés y diversión | RespiBAN (pecho, 700 Hz): ECG, EDA, EMG, respiración, temperatura, aceleración; Empatica E4 (muñeca): BVP 64 Hz, EDA 4 Hz, temperatura 4 Hz, aceleración 32 Hz | Formato descrito en su readme; la página no indica tamaño en bytes | La página de UCI no indica la licencia: no verificado | **RECHAZADO**: sin SpO2 ni FC directa (habría que derivarla de ECG/BVP), licencia no verificada, gran volumen |
| NASA OSDR — Inspiration4 (S22) | Repositorio con datasets abiertos | 4 astronautas civiles, misión de 3 días | Ómicas y paneles sanguíneos (OSD-569, -570, -571, -575) | Varios | Abierto (OSDR) | **RECHAZADO** para el pipeline: no contiene series de FC, SpO2, FR, sueño ni ánimo. Se cita como contexto de datos humanos reales de vuelo |
| NASA OSDR — Environmental Data App (S21) | Herramienta con tablas descargables | ISS (cabina) y control en tierra; misiones Rodent Research | Temperatura, CO2, humedad relativa, dosis de radiación | Tablas descargables | Pública | **RECHAZADO** para vitales: datos ambientales, no fisiológicos. Posible extensión futura como contexto ambiental |
| NASA LSDA / LSAH (S23) | Archivo con acceso por solicitud | Astronautas y sujetos de análogos | Datos clínicos y de investigación | No aplica | Requiere revisión, aprobación e IRB de NASA | **RECHAZADO**: no accesible en el tiempo del proyecto |
| NASA HRP (S25) y NASA-STD-3001 (S13) | Portales de evidencia, no datasets | — | — | — | — | Fuentes de evidencia, no de datos |

### Fuente seleccionada: PhysioNet BIDMC v1.0.0

- DOI 10.13026/C2208R. Licencia: Open Data Commons Attribution License v1.0
  (ODC-By), acceso abierto. Citas requeridas: S17, S18, S19.
- Archivos por sujeto (`##` = 01..53): `bidmc_##_Numerics.csv`, `bidmc_##_Signals.csv`,
  `bidmc_##_Breaths.csv`, `bidmc_##_Fix.txt`. Archivos raíz: `README`, `LICENSE`,
  `RECORDS`, `SHA256SUMS.txt`, `ANNOTATORS`, `DBS`.
- URL de archivo: `https://physionet.org/files/bidmc/1.0.0/bidmc_csv/bidmc_##_Numerics.csv`
  y `https://physionet.org/files/bidmc/1.0.0/bidmc_csv/bidmc_##_Fix.txt`.
  Checksums oficiales: https://physionet.org/files/bidmc/1.0.0/SHA256SUMS.txt
- Header exacto de Numerics (con espacio tras cada coma): `Time [s], HR, PULSE, RESP, SpO2`.
- `bidmc_01_Numerics.csv`: 481 filas de datos (Time 0..480 s, sin huecos); NaN en
  PULSE y SpO2 entre Time 111 y 123. Primera fila: 0, 94, 93, 25, 97.
- `bidmc_01_Fix.txt` describe un paciente de 88 años, sexo masculino, en MICU,
  identificador MIMIC II s01182, y un segmento con fecha desplazada (año 2688) por
  desidentificación: esas fechas NO son reales y NO deben convertirse en timestamps UTC.
- Sujetos seleccionados: `bidmc_01`, `bidmc_02`, `bidmc_03` (solo Numerics y Fix).
- Son pacientes terrestres de UCI `[TERRESTRIAL-CLINICAL]`. Nunca se etiquetan como
  astronautas ni se cargan en la API de astronautas.

## Sources / Fuentes

- **S13** NASA-STD-3001 Technical Briefs (OCHMO). https://www.nasa.gov/ochmo/health-operations-and-oversight/hsa-standards/
- **S17** PhysioNet — BIDMC PPG and Respiration Dataset v1.0.0. https://physionet.org/content/bidmc/1.0.0/ DOI 10.13026/C2208R. ODC-By v1.0.
- **S18** Pimentel MAF et al. Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters. IEEE Trans Biomed Eng. 2016;64(8):1914–1923. DOI 10.1109/TBME.2016.2613124.
- **S19** Pollard T, Moody BE, Lehman L, Gow B, Fernandes C, Xie C, Johnson A, Mark RG, Heldt T. PhysioNet as a global platform for biomedical research. Nature Health (2026). DOI 10.1038/s44360-026-00096-z.
- **S20** UCI ML Repository — WESAD (Wearable Stress and Affect Detection), id 465. https://archive.ics.uci.edu/dataset/465/wesad DOI 10.24432/C57K5T. Schmidt P, Reiss A (2018).
- **S21** NASA OSDR — Environmental Data App (EDA). https://visualization.osdr.nasa.gov/eda ; NTRS 20240008072.
- **S22** Sanders LM et al. Inspiration4 data access through the NASA Open Science Data Repository. npj Microgravity 2024;10:56. DOI 10.1038/s41526-024-00393-5. PMCID PMC11094041.
- **S23** NASA LSDA / LSAH — data request. https://nlsp.nasa.gov/explore/lsdahome/datarequest
- **S25** NASA HRP. https://www.nasa.gov/hrp/
