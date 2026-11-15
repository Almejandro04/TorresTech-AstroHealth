# Frontend acceptance evidence

Baseline: main 0f377776083a37f6624be3700d3b853d5d2001ef. This continuation uses its own checkout and codex/frontend-api-and-demo-20261115 branch; it preserves Flight Log and the v0.1.0 contract.

## Evidence and scope

The prior Flight Log review verified four-view navigation, desktop/mobile layouts, original indicator dates/units/provenance, chart/data-table behavior, alert detail, replay, journal cancel/save/rejected/unconfirmed recovery, Back/Forward, empty profiles, unavailable analysis and read failures. Captures and exact limits are in docs/design/redesign_rationale.md.

This continuation adds:
- 94-pair contrast check and the existing shared mock response/write/error/replay checks.
- 9 series/journal-default checks: chronology, four required chart metrics, empty/single-point data, actual React server rendering of empty/single-point chart components, separate contexts, gaps, zero sleep, unavailable references and correction metadata.
- 15 Fetch-client checks over an actual test-only HTTP server: all shared successful response guards, health/profiles/summary/history/alerts, filters/pagination/cutoff, create/correct/retry, malformed JSON/schema, 404/422/500, disconnects/timeouts, wrong profiles/future data and wrong-day write confirmations.
- Real FastAPI health request through the same Fetch client and all 8 existing backend tests.

React server-render checks are not a claim of a new browser layout review. After the API mode initially displayed its Dashboard and correctly blocked new journal creates without configured metadata, the browser review was interrupted because Windows URL verification could not continue. Actual 200% zoom, the configured-create UI after reload, and the new failure/recovery controls still require browser verification. Tests cover transport behavior; they do not prove FastAPI/SQLite mission integration.

## Issue mapping

| Issue | Functional evidence | Disposition |
| --- | --- | --- |
| #10 Dashboard | Five typed snapshots with independent times/units/context; null/earlier values, shared mock source, navigation and narrow-layout checks from Flight Log review | Mock dashboard acceptance covered |
| #11 Analytics | Four vital/sleep histories; period selection; reference/insufficient states; unit and actual component render edge-case checks; no cross-context interpolation | Mock analytics acceptance covered |
| #12 Alerts | Shared normal/change/unavailable fixtures, detail/evidence/source, text/icon severity/status, read-only lifecycle, existing visual/error checks | Mock alerts acceptance covered |
| #17 Journal | Form/mock workflow and HTTP adapter exist, writes preserve identity/input and require explicit create metadata | Keep open: actual API-backed persistence/history not verified |
| #13 Integration | Explicit mock/API mode, central Fetch client, runtime wire guards, refresh actions and errors | Keep open: actual mission backend/ingestion absent |
| #22 README/demo | Current setup, architecture/roles, truthful capabilities, source links, demo/fallback/reset and integration runbook | Keep open: final integrated rehearsal depends on #21 |
| #21 E2E | Detailed procedure, real health proof, fixture/transport tests and known blockers | Keep open: no persisted mission path yet |

The new Refresh data action reloads profiles/summary/history/alerts through the current source without rewriting URL selections. It is supplied on Dashboard/Analytics/Alerts; Journal refresh follows a confirmed write. A profile-list failure is now rendered by the shared page header, so non-Dashboard views do not silently show an empty workspace.

## Remaining limitations

The build still emits Vite's advisory chunk-size warning. The backend owns request validation, record identity, scientific rules and database transactions; frontend guards check supported wire shapes and requested identity/cutoff, not medical correctness or every backend invariant. The original synthetic seed and the explicit test-only HTTP fixture must remain distinct from real biomedical source records and the planned 30-day generator.

### API review reload observation

During an environment-file restart while running separate mock/API dev servers, the API review tab became blank. The API configuration and source-selection modules loaded successfully in a Node/Vite probe. Dev dependency caches are now separated by mode, preventing concurrent-mode cache replacement; that change still needs a rendered browser recheck. Browser automation stopped before configured-create and failure/recovery interaction tests could complete. This observation remains an explicit #13 integration review item, not a claim of a fixed/render-verified API UI.
