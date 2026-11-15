# AstroHealth — TorresTech

An English-language educational prototype for monitoring a fictional astronaut mission. Flight Log displays vital observations, daily self-reports, individual reference comparisons and explainable experimental alerts.

**Current supported demo: synthetic frontend data, with no backend required.** The real FastAPI service currently exposes only `GET /api/health`. The Fetch client is implemented and selectable, but persisted mission integration is blocked until the backend/data issues are delivered. This project is not a validated diagnostic system and is not affiliated with or endorsed by NASA.

## Current capabilities

| Area | Available now | Remaining |
| --- | --- | --- |
| Dashboard | Five indicators with original timestamps/units/context/provenance; missing and earlier readings stay identifiable | Persisted API data verification |
| Analytics | Vital and daily-journal charts, periods, individual reference, explicit gaps, accessible tables | Final cross-browser/accessibility review |
| Alerts | Read-only list/detail, status and explanation; labeled extra presentation samples | Real backend rule engine |
| Journal | Validate/create/correct in mock mode; typed HTTP writes and safe uncertain-write handling | FastAPI/SQLite persistence verification |
| API | Real health endpoint, OpenAPI/Swagger, configurable CORS | Mission storage, ingestion, analysis and endpoints |
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

## Backend: verified bootstrap

Prerequisite: Python 3.11 or newer compatible with pinned requirements. The author verified 3.13.3; the bootstrap/health tests were also verified with 3.14.5.

```powershell
# Repository root
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
$env:ASTROHEALTH_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
cd backend
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

Health success does not mean the astronaut endpoints or SQLite are implemented.

## Select the real HTTP transport

In a local `frontend/.env.local` (restart Vite after configuration changes):

```dotenv
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=10000
```

`VITE_DATA_SOURCE=mock` restores the explicit in-memory demo. A failed real API never falls back to bundled fixtures. The API mode initially reports mission endpoint failures while the backend is bootstrap-only; this is expected, not a successful data integration. Add the exact browser origin/port to backend CORS, including a separate review port if used.

For **new live journal entries**, explicitly configure the imported mission manifest and agreed effective UTC time through `VITE_JOURNAL_SOURCE_ID` and `VITE_JOURNAL_TIME_UTC=HH:MM:SS`. They are not credentials and are public frontend configuration. New creates stay disabled until both are configured; corrections retain their original timestamp/source. Only use SYN-CORE-001 / 08:00:00 for the matching contract fixture mission. Configure the actual generator's manifest for other missions.

## Architecture and ownership

| Layer | Implementation / target | Owner |
| --- | --- | --- |
| UI and transport | React, TypeScript, Vite, Tailwind, Lucide, Recharts; HealthDataSource interface, Fetch or mock adapter | Jorge — [@Almejandro04](https://github.com/Almejandro04) |
| Backend | FastAPI/Pydantic bootstrap available; Pandas/SQLite ingestion, persistence and analysis planned | Jhonatan — [@TheJhonatan144](https://github.com/TheJhonatan144) |
| Data and scientific evidence | Contract fixture available; source selection, processing and synthetic generator pending | Ismael — [@BrandonFreire](https://github.com/BrandonFreire) |

The UI reads through one typed interface, so transport selection does not replace Flight Log views. Physiological/journal cadences remain separate. Cutoffs and timestamps are UTC. The backend owns baseline/alert rules; mock calculations illustrate the agreed fixture cases and do not establish medical thresholds.

## Data, evidence and limitations

- [Accepted API/data contract v0.1.0](docs/api_contract.md), [shared examples](docs/examples/api_examples.json), [seed manifest](docs/examples/mission_seed.json), [readings CSV](docs/examples/readings.csv), [journal CSV](docs/examples/journal.csv).
- [UX requirements](docs/ux_requirements.md), [Flight Log rationale and captures](docs/design/redesign_rationale.md), [acceptance evidence](docs/testing/frontend_acceptance.md).
- Scientific dictionary/source selection remain [#4](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/4) and [#5](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/5). No real biomedical source/license has been selected in main yet.
- Processing and the roughly 30-day synthetic export remain [#16](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/16) and [#6](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/6). No generator/import/reset CLI is claimed before it exists.
- Journal source/time, baseline assumptions and introduced changes are simulation conventions. All current demo profiles/measurements are fictional; terrestrial patients must never be relabeled as astronauts.

## Team workflow

Use a separate checkout and personal task branch from current `main`. Commit and push reviewable changes, fetch again before integration, preserve teammates' commits and resolve conflicts explicitly. The owner permits direct merges/pushes by existing collaborators with write access; PRs remain optional. Do not force-push shared branches. Database/data changes belong to their owners; preserve the approved contract or coordinate a documented change first.

## Integration and next steps

[Integration smoke procedure](docs/architecture/integration_smoke_test.md) distinguishes passing checks from blocked persistence/replay paths. [Autonomous work report](docs/autonomous_progress.md) records this work and remaining issues.

Live integration (#13), API-backed Journal (#17), full integration testing (#21), and the final end-to-end demo rehearsal (#22) remain dependent on backend/data delivery. The JavaScript bundle still exceeds Vite's advisory 500 kB threshold; the warning is visible rather than suppressed.
