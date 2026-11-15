# AstroHealth — TorresTech

An English-language educational prototype for monitoring a fictional astronaut mission. Flight Log displays vital observations, daily self-reports, individual reference comparisons and explainable experimental alerts.

**Two explicit modes: the Flight Log mock demo and the real FastAPI/SQLite transport.** The backend now stores fictional profiles, readings and journal entries, exposes their REST endpoints, and supports atomic JSON/CSV import and staged mission days. Real Fetch-client, replay and restart-persistence checks pass with the seven-day contract seed. Current API/Journal browser acceptance is verified; DATA-04 and calculated baselines/alerts remain pending. This project is not a validated diagnostic system and is not affiliated with or endorsed by NASA.

## Current capabilities

| Area | Available now | Remaining |
| --- | --- | --- |
| Dashboard | Five indicators with original timestamps/units/context/provenance; missing and earlier readings stay identifiable | Full DATA-04/analysis scenario |
| Analytics | Vital and daily-journal charts, periods, individual reference, explicit gaps, accessible tables | Final cross-browser/accessibility review |
| Alerts | Read-only list/detail, status and explanation; labeled extra presentation samples | Real backend rule engine |
| Journal | Mock workflow and real HTTP create/correct/retry; SQLite persistence across restart verified | Broader assistive/cross-browser review |
| API | SQLite, profiles/readings/journal/summary/alerts routes, JSON/CSV import, staged days, explicit CORS, Swagger | Calculated references/trends and alert engine (#14/#15) |
| Data | Seven-day contract seed, two fictional profiles, fixtures/CSV examples | Reproducible 30-day generator and real-data research/processing |

The planned mission timeline is 30 days; the shared seed contains seven observed days, not 30 generated days.

## Quick start: frontend demo

Prerequisite: Node.js `^20.19.0 || >=22.12.0` and npm. Verification used Node 25.9.0 / npm 11.12.1. From a fresh checkout:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173/#/dashboard. No environment file is required: data source defaults to `mock`. Vite uses a strict port; if another teammate owns 5173, use `npm run dev -- --port 5175` rather than stopping their process.

Light is the default; dark theme is user-selected. Synthetic demo settings and journal changes last for the page session. Reloading restores the seed. Follow the [demo runbook](docs/demo_runbook.md).

```powershell
npm run check
npm run build
npm run preview
```

The production preview defaults to port 4173. Build includes TypeScript. The check suite covers contrast, shared mock responses, chart/series edge cases and the real Fetch adapter against an explicitly test-only HTTP fixture.

## Backend: SQLite and REST API

Prerequisite: Python 3.11 or newer compatible with pinned requirements. The backend author verified 3.13.3; this integration continuation verified the full backend suite and real smoke on 3.14.5.

```powershell
# Repository root
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
$env:ASTROHEALTH_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
cd backend
# New disposable demo database; preserve any existing working database.
$env:ASTROHEALTH_DB_PATH = Join-Path $env:TEMP ("astrohealth-demo-" + [guid]::NewGuid().ToString("N") + ".db")
..\.venv\Scripts\python.exe -m app.database import-json ..\docs\examples\mission_seed.json --until-day 3
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Health: http://127.0.0.1:8000/api/health. Swagger: http://127.0.0.1:8000/docs. Schema: http://127.0.0.1:8000/openapi.json.

```powershell
# From backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m pip check
```

From `frontend`, the actual Fetch client's read-only health probe is:

```powershell
npm run check:health -- http://127.0.0.1:8000
```

Health alone checks the service. Mission endpoints and SQLite are implemented; the isolated integration smoke below checks their real behavior. No baseline/alert evaluation is claimed from a successful import.

## Select the real HTTP transport

In a local `frontend/.env.local` (restart Vite after configuration changes):

```dotenv
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=10000
```

`VITE_DATA_SOURCE=mock` restores the explicit in-memory demo. A failed real API never falls back to bundled fixtures. Initialize/import the selected database before expecting profiles and mission data. Empty profiles and unavailable analysis are separate from request failure. Add the exact browser origin/port to backend CORS, including a separate review port if used.

For **new live journal entries**, explicitly configure the imported mission manifest and agreed effective UTC time through `VITE_JOURNAL_SOURCE_ID` and `VITE_JOURNAL_TIME_UTC=HH:MM:SS`. They are not credentials and are public frontend configuration. New creates stay disabled until both are configured; corrections retain their original timestamp/source. Only use SYN-CORE-001 / 08:00:00 for the matching contract fixture mission. Configure the actual generator's manifest for other missions.

## Reproducible real integration smoke

From the repository root, after installing backend development dependencies:

```powershell
.\.venv\Scripts\python.exe scripts\check_local_integration.py
# If Node is not on PATH:
.\.venv\Scripts\python.exe scripts\check_local_integration.py --node "C:\Program Files\nodejs\node.exe"
```

This additional smoke requires Node **22.13+** because the existing backend client probe loads the unchanged TypeScript client in memory. It uses a new temporary database and its own loopback server/ports, imports days 3 -> 5 -> 7, checks historical cutoffs/idempotence/CORS, executes eight real frontend Fetch/history checks, and restarts FastAPI to verify journal corrections and reading identity. It stops its own server and removes its disposable database. It does not test the browser or generate DATA-04.

For interactive staged replay, run the same import with `--until-day 5` in another backend terminal with the **same absolute ASTROHEALTH_DB_PATH**. Repeating it creates no duplicate readings. Going backwards preserves stored future rows: use `post_import.cutoffs[astronaut_id]` as API `as_of`; `latest_stored_cutoffs` identifies the physical latest observation. Offline `reset` loads the full seed and is not an empty replay start. Never reset a teammate’s working database.

## Architecture and ownership

| Layer | Implementation / target | Owner |
| --- | --- | --- |
| UI and transport | React, TypeScript, Vite, Tailwind, Lucide, Recharts; HealthDataSource interface, Fetch or mock adapter | Jorge — [@Almejandro04](https://github.com/Almejandro04) |
| Backend | FastAPI/Pydantic REST routes, SQLite persistence, JSON/CSV ingestion and staged replay; Pandas analysis/rules pending | Jhonatan — [@TheJhonatan144](https://github.com/TheJhonatan144) |
| Data and scientific evidence | Contract fixture available; source selection, processing and synthetic generator pending | Ismael — [@BrandonFreire](https://github.com/BrandonFreire) |

The UI reads through one typed interface, so transport selection does not replace Flight Log views. Physiological/journal cadences remain separate. Cutoffs and timestamps are UTC. The backend owns baseline/alert rules; mock calculations illustrate the agreed fixture cases and do not establish medical thresholds.

## Data, evidence and limitations

- [Accepted API/data contract v0.1.0](docs/api_contract.md), [shared examples](docs/examples/api_examples.json), [seed manifest](docs/examples/mission_seed.json), [readings CSV](docs/examples/readings.csv), [journal CSV](docs/examples/journal.csv).
- [UX requirements](docs/ux_requirements.md), [Flight Log rationale and captures](docs/design/redesign_rationale.md), [acceptance evidence](docs/testing/frontend_acceptance.md).
- Scientific dictionary/source selection remain [#4](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/4) and [#5](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/5). No real biomedical source/license has been selected in main yet.
- Processing and the roughly 30-day synthetic export remain [#16](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/16) and [#6](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/6). The generator remains pending. Import and database init/seed/reset commands now exist in [backend/README.md](backend/README.md); they do not generate a 30-day mission.
- Journal source/time, baseline assumptions and introduced changes are simulation conventions. All current demo profiles/measurements are fictional; terrestrial patients must never be relabeled as astronauts.

## Team workflow

Use a separate checkout and personal task branch from current `main`. Commit and push reviewable changes, fetch again before integration, preserve teammates' commits and resolve conflicts explicitly. The owner permits direct merges/pushes by existing collaborators with write access; PRs remain optional. Do not force-push shared branches. Database/data changes belong to their owners; preserve the approved contract or coordinate a documented change first.

## Application loading and consistent views

The loading/recovery shell imports the application separately, so a rejected application chunk or connection configuration can show a reload action instead of leaving an empty root. Route/render errors have the same recovery frame; unsaved Journal changes may be lost on reload. Raw configuration values and stack traces are not displayed. Loading/configuration recovery and the supported restart sequence are now browser-verified; see the acceptance evidence below.

History, journal and alert requests share the displayed summary’s observation cutoff, including the latest view. A later reading appears after Refresh data advances that summary. Missing pages, repeated offsets or changing pagination totals are errors rather than partial history shown as complete.

## Browser acceptance

[Rendered API/Journal checks and captures](docs/testing/browser13_acceptance.md) cover staged import, filters/replay, offline/retry, persisted Journal create/correct and reload. A separate contract HTTP fixture verifies alert rendering readiness; actual generated alerts remain #15/#21.

## Integration and next steps

[Integration smoke procedure](docs/architecture/integration_smoke_test.md) separates verified real transport/persistence from remaining browser/science checks. [Current integration results](docs/testing/integration_update_20261115.md) and [#13 recovery/cutoff update](docs/testing/frontend13_update.md) supersede the older bootstrap-only snapshot in the [historical autonomous report](docs/autonomous_progress.md).

Current API view/Journal acceptance (#13/#17) is complete. Full integration (#21) and final demo rehearsal (#22) remain open for DATA-04, actual analysis/rules, measured zoom and broader accessibility. The JavaScript bundle still exceeds Vite's advisory 500 kB threshold; the warning is visible rather than suppressed.
