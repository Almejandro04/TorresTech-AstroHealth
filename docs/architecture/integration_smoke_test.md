# Integration smoke test — contract v0.1.0

Owners: Jorge (@Almejandro04) and Jhonatan (@TheJhonatan144); data support: Ismael (@BrandonFreire).

## Evidence levels

| Check | Evidence | Status |
| --- | --- | --- |
| UI contract fixture demo | Shared seed/mock checks, existing desktop/mobile review | Passed for the mock prototype |
| Fetch wire transport | scripts/check-api.mjs: actual HTTP requests to a test-only fixture server | Passed; not FastAPI/SQLite evidence |
| Real service bootstrap | scripts/check-health.mjs against FastAPI; backend pytest | Passed; only /api/health exists |
| Imported mission -> SQLite -> API | Requires backend storage/API/ingestion and DATA-04 | Blocked |
| Real reference/change/alert replay | Requires backend analysis/rules and imported scenario | Blocked |
| Actual browser zoom 200%, new API-write/failure flows | Browser automation was interrupted before completion | Pending |

Never treat a test fixture server, a page-session mock save, or a successful health request as proof of database persistence.

## Commands that exist now

From frontend: npm ci, npm run check, npm run build, npm run preview. Individual checks: check:contrast, check:mocks, check:series, check:api. The read-only real-backend probe is npm run check:health -- http://127.0.0.1:8000.

From backend: install requirements-dev.txt in an isolated venv, run python -m pytest and python -m pip check. Start python -m uvicorn app.main:app on an unoccupied port; configure ASTROHEALTH_CORS_ORIGINS for the actual browser origin. Exact PowerShell setup appears in the root README and backend README.

There is currently no verified generation/import/SQLite-reset/replay CLI in main. Obtain those commands from #6/#7/#9 when delivered. Do not manually fabricate database rows to make this smoke test pass.

## Clean-start integrated sequence, once dependencies land

1. Record commit SHA, Python/Node versions, synthetic manifest/schema version, generator seed and supported commands.
2. Create an isolated demo database using the backend's documented path/configuration. Generate/import/reset through the documented CLI. Repeating the supported import must follow its idempotency policy.
3. Start FastAPI and Vite. Set VITE_DATA_SOURCE=api and the correct API base. Allow the exact frontend origin through CORS; no wildcard is required.
4. Confirm profiles, readings, journal, summary and alerts respond with v0.1.0 envelopes. Unknown profiles must return normalized 404 and malformed fields/filters 422.
5. Compare the selected astronaut/day, every latest snapshot, units, original timestamps/context/provenance and chart/table values with persisted source records. Use backend-generated IDs, not assumed fixture IDs.
6. Select the reference period, then advance the documented replay through introduced changes. Refresh data without losing the selected profile/range. Confirm no future readings, reference windows or later resolution status leak into historical views.
7. Verify a read-only alert explanation includes the observed value/pattern, individual reference/window, rule version, attention level and source. Repeat replay and confirm deterministic output/deduplication.
8. Check empty history, null metric, isolated spike, insufficient reference and unavailable-analysis states separately. No error or unknown state may appear as normal health.
9. Stop the API. All views must distinguish failed reads from empty data and offer a recovery path. Restart and retry. Do not silently switch to mocks.
10. For Journal, configure the imported mission source/effective UTC time before enabling creates. Verify 201 create, 200 correction/exact retry, stable daily ID, retained input on 422/network failure and uncertainty after an unconfirmed POST. Reload and restart the backend to prove persistence; verify summary/sleep history refresh.
11. Run at desktop/mobile widths and actual 200% browser zoom in both themes; use keyboard/assistive technology for focus, dialogs, radios/selects, skip link and chart tables.
12. Log each defect with exact steps, expected/actual values, owner and commit. Recheck affected paths after fixes.

## Defect record template

| Field | Record |
| --- | --- |
| Scenario / commit / source | Exact fixture or imported mission and revision |
| Steps | Commands, route/profile/range and action |
| Expected / actual | Include API values and UI evidence |
| Component / owner | Frontend, backend or data |
| Priority / issue | P0 blocker versus deferred follow-up |
| Fix / retest | Commit and observed outcome |

## Current blockers

#6 synthetic generation, #7 storage, #8 mission API, #9 ingestion/replay, #14 analysis and #15 alert engine are not delivered in the reviewed main baseline. Do not close #13, #17 or #21 on transport-only evidence. Final end-to-end demo rehearsal in #22 remains pending.

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
