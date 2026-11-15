# AstroHealth demonstration runbook

## Scope

- **Main demo:** the 30-day synthetic mission (`SYN-AH-MISSION-001`, AST-101 and AST-102) in **API mode**, with the real FastAPI/SQLite backend calculating baselines and alerts. The expected values below come from [`data/synthetic/scenario_manifest.json`](../data/synthetic/scenario_manifest.json) and the recorded [#21 results](testing/integration21_results.md).
- **Plan B:** the frontend **mock demo** with the seven-day contract fixtures, clearly labeled **Synthetic demo**. Its alert is an illustration, not a backend result.

Everything shown is synthetic data for fictional astronauts. Baselines and the alert rule are experimental; nothing here is a diagnosis.

## Reset / rehearsal checklist (before presenting)

1. New disposable database, in the backend terminal from the repository root:

   ```powershell
   $env:ASTROHEALTH_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
   $env:ASTROHEALTH_DB_PATH = Join-Path $env:TEMP ("astrohealth-demo-" + [guid]::NewGuid().ToString("N") + ".db")
   cd backend
   ..\.venv\Scripts\python.exe -m app.database import-json ..\docs\examples\mission_seed.json --until-day 7
   ..\.venv\Scripts\python.exe -m app.database import-json ..\data\synthetic\mission_ast101_ast102.json --until-day 30
   ```

2. From the repository root, both green (each uses its own temporary database):

   ```powershell
   .\.venv\Scripts\python.exe scripts\check_local_integration.py
   .\.venv\Scripts\python.exe scripts\validate_mission_rules.py
   ```

3. Start the API: `..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` (from `backend`, same terminal and database path). Check http://127.0.0.1:8000/api/health.
4. `frontend/.env.local` contains `VITE_DATA_SOURCE=api`, `VITE_API_BASE_URL=http://localhost:8000`, `VITE_JOURNAL_SOURCE_ID=SYN-AH-MISSION-001`, `VITE_JOURNAL_TIME_UTC=08:00:00`. Start Vite (`npm run dev` in `frontend`).
5. Browser on http://127.0.0.1:5173/#/dashboard, profile **AST-101**, latest view. The mission bar shows **API · synthetic mission data**.
6. Choose the theme (light is the default) and a readable zoom for the room.
7. Plan B ready: a second checkout or terminal able to run the mock demo (below).

## Presentation script (~2–3 minutes)

| Step | Action | What to say |
| --- | --- | --- |
| 1 — identity | Dashboard, AST-101; point to the mission bar | A fictional astronaut on a 30-day synthetic mission. The bar says **API · synthetic mission data**: every value comes from the backend and keeps its time, context and source. |
| 2 — reference | Mission view **Day 5**, then **Day 6–8** | Day 5: **More observations needed** — the reference window (days 1–5) has not ended, so nothing is compared and this is not an all-clear. From day 6: an individual reference of about 72 beats/min (72.2), from 5 resting observations only. |
| 3 — isolated spike | Mission view **Day 9** | Resting heart rate is high on day 9 (84) but there is no alert: the experimental rule needs two consecutive days at or above reference + 5. |
| 4 — missing data | Mission view **Days 12–14**; Analytics | Day 12 has no resting heart rate, day 13 no resting respiratory rate, day 14 no journal entry. Charts show gaps and "Not recorded", never 0. A card may show the latest non-null value from another context (for example the day-12 exercise heart rate) with that context visible. |
| 5 — introduced change | Mission view **Day 19**; Alerts | A **warning** from `DEMO-HR-CHANGE` version `fixture-1`: window days 18–19, observed 80 versus reference 72.2. Read the explanation. The +5 beats/min / two-day rule is a simulation assumption, not a clinical threshold. |
| 6 — resolution | Mission view **Day 22** | Day 22 is back below the threshold, so the same alert is **resolved**. Earlier days still show it as it was then. |
| 7 — insufficient history | Profile **AST-102** | Only three days of data: **More observations needed**. The system never presents missing analysis as "no alerts". |
| 8 — optional journal | Journal, AST-101; save a note | A saved entry is stored in SQLite; the summary and sleep history refresh from the API. |

Closing (honest): "The reference is a fixed-window mean of days 1–5 at rest, and the alert is one experimental rule. All data is synthetic, generated reproducibly; terrestrial PhysioNet data is processed separately and never shown as an astronaut. This is a monitoring prototype, not a diagnostic tool, and it is not endorsed by NASA."

## Likely questions

| Question | Short answer |
| --- | --- |
| Is the data real? | No. Astronauts and the mission are synthetic ([data/synthetic/README.md](../data/synthetic/README.md)). A small terrestrial ICU subset (PhysioNet BIDMC, ODC-By) is processed separately and never enters the astronaut views ([data_sources.md](data_sources.md)). |
| Why +5 beats/min? | It is a simulation assumption for the demo; no cited source supports it as a threshold ([validation_review.md](research/validation_review.md), [alert_rules.md](architecture/alert_rules.md)). |
| What happens without data? | The status is `insufficient_data` ("More observations needed"), never an empty "no alerts" result. |
| How do you avoid inventing values? | Nulls stay null, absent entries stay absent, contexts are never mixed, mood is never averaged, and every value keeps its own timestamp and source ([analysis.md](architecture/analysis.md)). |
| How is it reproduced? | Seed 2026 regenerates byte-identical files; `validate_mission_rules.py` and `check_local_integration.py` check the scenario over the real backend ([integration21_results.md](testing/integration21_results.md)). |

## Failure / empty-state rehearsal

- **API stopped:** stop uvicorn; the views show an error state with **Try again**, never bundled fixtures. Restart uvicorn with the same database path and retry.
- **AST-102:** short history, `insufficient_data` / "More observations needed".
- **Null values:** days 12–13 stay chart gaps even when a card shows an earlier or other-context value with its own time.
- **Journal failures:** a rejected or unconfirmed save keeps the draft and explains the uncertainty.

## Plan B — mock demo

In `frontend`, remove or rename `.env.local` (or set `VITE_DATA_SOURCE=mock`), then `npm ci` if needed and `npm run dev`. The mission bar shows **Synthetic demo**; the data is the seven-day contract fixtures (AST-001, AST-002), not the 30-day mission.

1. Dashboard, AST-001. Reload resets session journal data and demo switches (or use **Restore seed data**).
2. Mission view Day 5, then Day 7: on Day 7 the resting heart rate is 84, oxygen 97%, sleep 5.5 h and mood 2; respiratory rate keeps its Day 6 value because Day 7 is null.
3. Alerts: the fixture warning (days 6–7 mean 81 versus reference 72). **Say clearly that this alert is an illustrative contract fixture, not one generated by the backend.**
4. Demo scenarios: "Analysis not implemented" differs from evaluated-no-alerts; "Requests fail" shows the error and **Try again**.

The committed Flight Log captures ([redesign rationale](design/redesign_rationale.md)) are an illustration if the browser fails, not proof of a running backend.
