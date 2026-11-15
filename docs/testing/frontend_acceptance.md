# Frontend acceptance evidence

## Current integration status — 2026-11-15

Flight Log and contract v0.1.0 are preserved. The original functional review was based on 0f37777; the backend has since delivered SQLite, REST routes and staged import, and 9e94071 fixes the historical import handoff. The [current integration report](integration_update_20261115.md) supersedes earlier bootstrap-only blocker descriptions.

## Evidence and scope

The prior Flight Log review verified four-view navigation, desktop/mobile layouts, original indicator dates/units/provenance, chart/data-table behavior, alert detail, replay, journal cancel/save/rejected/unconfirmed recovery, Back/Forward, empty profiles, unavailable analysis and read failures. Captures and exact limits are in [the design rationale](../design/redesign_rationale.md).

Current executed checks:
- Clean npm ci, TypeScript and default/API-mode production builds.
- All 94 contrast pairs, existing contract mock/write/error/replay checks, 9 series/default checks and 15 HTTP-fixture client checks.
- Backend: 307 tests pass with 6 expected analysis/alert failures.
- Actual FastAPI/SQLite: unchanged frontend Fetch client passes seven checks covering profiles, summary/history/cutoff/pagination, empty/unavailable states, 404/422, journal create/correct/retry and reading conflicts.
- The new root scripts/check_local_integration.py additionally checks staged import over HTTP, historical replay handoff without deleting later records, CORS and journal/reading persistence after service restart.

Fixture transport tests are distinct from the real SQLite/HTTP smoke. Neither is a new browser review. The prior API Dashboard/unconfigured-create gate was seen through the HTTP fixture; the configured-create reload became blank and remains R1 below.

## Issue mapping

| Issue | Evidence | Disposition |
| --- | --- | --- |
| #10 Dashboard | Typed indicator snapshots, timestamps/units/context/null/earlier data, navigation and prior narrow-layout checks | Closed mock-scoped acceptance |
| #11 Analytics | Four charts, periods, gaps/reference states, actual component-render empty/single-point checks | Closed mock-scoped acceptance |
| #12 Alerts | Typed read-only detail/evidence/source, text/icon severity/status, no-alert/unavailable/failure distinction | Closed mock-scoped acceptance |
| #13 API | Explicit mode, typed Fetch and real persisted responses, filters/cutoffs/errors | Open: rendered range/refresh/recovery and R1 review |
| #17 Journal | Form/mock workflow, real create/correct/retry/history/summary and restart persistence | Open: rendered configured-create/error/focus/refresh review |
| #21 E2E | Reproducible real import/API/client/restart smoke | Open: DATA-04, #14/#15 and full rendered scenario/accessibility |
| #22 README/demo | Current setup, truthful capabilities/roles, CLI/config and distinct API/mock demo | Open: scientific source deliverables and final integrated rehearsal |

The shared Refresh data action reloads through the selected source while preserving URL profile/range selections; Journal refresh follows confirmed writes. Profile-list failures render on every page header. These code paths still need the new rendered API acceptance checks; transport success does not prove those interactions.

## API review reload observation — R1

During an environment-file restart with concurrent mock/API dev servers, the API review tab became blank. API config/source selection and both production builds pass. Dependency caches are separated by mode, but the proposed correction is not rendered-retested. The [integration runbook](../architecture/integration_smoke_test.md) records exact steps, expected/actual result, owner and pending retest.

Windows Computer Use stopped because it could not verify the browser URL confidently. No further UI automation was attempted. Actual browser zoom 200%, new API configured-create/failure/recovery controls, and broader assistive/cross-browser checks remain pending.

## Limits

The approximately 787 kB JavaScript bundle still emits Vite's advisory chunk warning. Wire/profile/cutoff guards do not establish medical correctness or every backend invariant. Current real smoke data is the seven-day CORE-01 seed; it is distinct from real biomedical records and Ismael's pending 30-day DATA-04 export. API baselines/alerts remain not_implemented until #14/#15.
