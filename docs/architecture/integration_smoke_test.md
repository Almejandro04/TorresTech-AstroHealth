# Integration smoke test — contract v0.1.0

Owners: Jorge (@Almejandro04) and Jhonatan (@TheJhonatan144); data support: Ismael (@BrandonFreire).

## Current browser follow-up

[Browser acceptance and captures](../testing/browser13_acceptance.md) now cover actual API views, range/replay/refresh, no observations, unavailable analysis, offline/retry and persistent Journal create/correct. The supported R1 restart recheck passes and a lost-confirmation defect was fixed. #13/#17 are complete for this frontend scope; full DATA-04/analysis/actual generated alerts and #21/#22 remain pending. Earlier R1/pending-browser statements below are preserved as historical evidence. No actual 200% zoom or broader accessibility review is claimed.

## Evidence levels after backend integration

| Path | Evidence | Status |
| --- | --- | --- |
| Mock Flight Log | Shared fixtures and prior desktop/mobile/form review | Passed for the mock scope; #10/#11/#12 closed |
| Backend models/API/import | Full pytest suite after the replay fix | 307 passed; 6 expected #14/#15 xfails |
| Frontend Fetch -> real FastAPI/SQLite | Unchanged client probe, eight checks over HTTP | Passed, including journal create/correct/retry and reading conflict |
| Staged ingestion -> API | Day 3 -> 5, repeated import and backward cutoff | Passed with the seven-day CORE-01 seed |
| Restart persistence | Stored journal correction/zero sleep/stable ID and single reading after server restart | Passed in an isolated database |
| Actual API browser/form/error flows | R1 and configured-create/failure controls | Pending; no new browser review claimed |
| DATA-04 -> analysis -> generated alert -> UI | #6/#14/#15 plus rendered integration | Pending |

## One-command real smoke

Install backend development requirements using the root README. From the repository root, with Node 22.13+ available:

```powershell
.\.venv\Scripts\python.exe scripts\check_local_integration.py
# Optional explicit Node location
.\.venv\Scripts\python.exe scripts\check_local_integration.py --node "C:\Program Files\nodejs\node.exe"
```

The script creates a task-owned temporary database and loopback Uvicorn subprocess on an ephemeral port. It overrides only its child process environment, imports the seed through days 3/5/7, checks idempotence and historical cutoffs, performs an actual CORS preflight, runs the existing eight-check frontend Fetch/history probe, and restarts the service to compare persisted journal/readings. Owned processes/files are cleaned up even on failure. It never resets the configured working database or starts a browser.

Additional checks from frontend: npm ci, npm run check and npm run build. The fixture HTTP suite is still test-only; it is distinct from the real smoke. From backend: python -m pytest and python -m pip check. The read-only check:health tests only service health.

## Interactive integrated sequence

1. Record commit SHA, Python/Node versions, manifest/schema version and supported commands. The current supported input is docs/examples/mission_seed.json, not the still-pending DATA-04 export.
2. Use a new absolute ASTROHEALTH_DB_PATH. Import through day 3 with python -m app.database import-json ../docs/examples/mission_seed.json --until-day 3. The import initializes missing schema. An offline reset loads the full seed; it is not an empty replay start.
3. Start FastAPI. Set VITE_DATA_SOURCE=api and the correct API base before starting Vite; allow the exact browser origin via ASTROHEALTH_CORS_ORIGINS.
4. Compare profile identity/day and every latest snapshot, units, original timestamps/context/provenance and chart/table values with persisted API records. GET profiles/readings/journal/summary/alerts must use v0.1.0 envelopes; unknown profiles return normalized 404 and invalid fields/filters 422.
5. In a second terminal with the SAME database path, import through day 5, repeat it, then day 7. Refresh Flight Log without losing profile/range. Confirm stable IDs and no duplicates. Historical day 3 must exclude later observations; the import report's post_import.cutoffs supplies that selected view, while latest_stored_cutoffs reports physical storage.
6. Treat not_implemented baselines/alerts as unavailable analysis. Do not expect a generated warning until #14/#15 land. After that delivery, replay the introduced deviation and compare reference/window, observed pattern, rule version, attention level and provenance. Repeat for determinism/deduplication.
7. Check empty profile/history, null metric, isolated spike, insufficient versus unavailable reference and failed reads separately. Unknown data must not look normal.
8. Configure explicit imported journal source/time before creates. Verify 201 create, 200 correction/retry, stable ID and summary/sleep history refresh; retain draft on 422 or failure and uncertainty after an unconfirmed POST. Restart with the same database and recheck persistence.
9. Stop/restart the API and verify rendered error/retry on all views. Never fall back to fixtures silently.
10. Recheck R1 below, desktop/mobile layouts, actual 200% zoom, both themes, keyboard focus/dialogs/radios/skip link and accessible chart tables.
11. Once DATA-04 arrives, repeat the import/identity/history/scenario checks against its real manifest/export, then repeat after the analysis/alert engines land. Keep #9/#13/#17/#21/#22 open until their individual remaining criteria are met.

## Defect recording

Record scenario/commit/source, exact commands and route/profile/range, expected/actual API and UI values, component/owner, issue/priority, fix commit and observed retest. Transport results do not stand in for browser layout/focus/error checks.

## Remaining blockers

- #6: Ismael's reproducible mission dataset; the existing seven-day fixture is not that deliverable.
- #14/#15: actual baseline/trend calculations and experimental alert evaluation. Six strict expected failures reflect those missing cases.
- #13/#17: rendered API view/write/error acceptance, including R1 below.
- #21/#22: final supported end-to-end rehearsal, actual zoom and broader assistive/cross-browser review.
- A documented rest/null discrepancy for not_implemented baseline examples remains in the backend README; the HTTP shape guard accepts the pending null context, and no shared contract/fixture is edited here.

## R1 — API review reload became blank

| Field | Recorded observation |
| --- | --- |
| Source / revision | Shared seed through the explicitly test-only HTTP fixture; implementation now in 9b25de1 |
| Setup | Start `node scripts/serve-fixture-api.mjs` from frontend and use its printed URL as `VITE_API_BASE_URL` in ignored `.env.api-review`; set `VITE_DATA_SOURCE=api`. Run mock on `npm run dev -- --port 5175` and API on `npm run dev -- --mode api-review --port 5176`. |
| Steps observed | API Dashboard initially displayed fixture values. Open `/#/journal?entry=8`: missing metadata correctly disabled create. Add `VITE_JOURNAL_SOURCE_ID=SYN-CORE-001` and `VITE_JOURNAL_TIME_UTC=08:00:00`, restart API dev server and reload that tab while the mock server is running. |
| Expected / actual | Expected configured Journal form; actual blank root after reload, document loaded, no captured browser console error. |
| Component / owner / issue | Frontend / Jorge / #13; blocks completion of the new API browser review, not proof that production has the same failure. |
| Candidate correction / limits | Separate Vite dependency cache by mode. API config/source-selection probe and both production builds pass. This has not been rendered-retested, so R1 remains open. |
| Retest | Repeat Dashboard, configured create/correct, rejected/uncertain write, retry and API-stop/restart flows in a browser once URL verification is available. Windows Computer Use stopped because the browser URL could not be verified confidently. No automated UI workaround was attempted. |

Do not expose the fixture server outside loopback or present it as the FastAPI mission backend. Test environment files are local-only and not committed.

## #13 follow-up

History/journal/alerts now use the displayed summary cutoff, including latest view. The real smoke inserts a later same-day reading after a summary is fetched: the old view excludes it and a refreshed view includes it. Startup module/config errors and route/render errors have an independent recovery frame; missing/repeated/changing history pages reject instead of silently returning a partial dataset. Eight non-browser startup/view/history checks and eight real backend client checks pass.

The harness drains server diagnostics through pipes instead of a temporary log file to avoid a Windows cleanup file-lock race. Actual browser verification, including the original R1, remains pending; these changes do not establish its original cause or prove it fixed. See [the #13 report](../testing/frontend13_update.md).
