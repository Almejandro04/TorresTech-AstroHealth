# FRONTEND-06 (#13) — recovery and observation consistency

> Earlier non-browser snapshot. The later [browser acceptance](browser13_acceptance.md) completes the rendered #13/#17 checks and records the Journal confirmation fix; the pending-review statements below describe the earlier state.

Baseline: main c1e113b6be82b580d96ab3d252e60b419755f949. Separate local checkout and branch codex/frontend-13-recovery-20261115. Flight Log composition/themes/tokens, the approved HTTP contract and shared source fixtures are preserved.

## Changes

1. The main entry renders a small loading frame before dynamically importing App. Rejected entry-module/configuration loading reaches an independent error frame with a reload action; it does not depend on the service/config/router modules that may have failed. Route/render recovery is also installed. The frame uses existing Flight Log styles and preserves the current URL on reload; raw setup values and stack traces are not shown. Reload may discard unsaved journal edits.
2. MissionContext pins history, journal and alerts to the displayed summary's meta.as_of, including the latest view. A new later observation arriving between requests cannot enter those histories until Refresh data obtains a new summary. Historical replay still uses its requested UTC cutoff. This is observation-time consistency, not a transactional database revision: a backfilled observation may still arrive inside an existing cutoff.
3. Paginated history fetching is extracted into a pure service, preserving existing hook/page exports. Missing pages, repeated offsets or changing totals reject with INCONSISTENT_HISTORY rather than returning a partial dataset as complete. Retry reloads the whole filtered history.
4. The live backend probe now checks a concurrent later same-day reading: the old summary cutoff excludes it, the refreshed summary/history includes it, and alerts receive the same cutoff. The isolated runner verifies both stored readings survive restart with stable data. Server diagnostics use drained pipes to avoid an observed intermittent Windows temporary-log cleanup lock.

## Executed checks

| Check | Result |
| --- | --- |
| npm run check | Passed: 94 contrast pairs, shared mocks, 9 series/default checks, 15 HTTP-fixture client checks and 8 new startup/view/history checks |
| New non-browser regression cases | Valid startup; invalid URL/mode/time recovery markup; module/startup-callback rejection; pinned cutoff then refresh; range/null gap; read-failure recovery; 1001-record pagination; inconsistent page rejection |
| npm run build | Passed, including TypeScript |
| API-mode production build | Passed in separate temporary output |
| Real FastAPI/SQLite smoke | Passed; 8 actual client/history checks plus staged import, CORS and restart persistence |
| Code/data boundaries | No contract/example or backend runtime/model/rule changes |

No dependencies were added. Current default JavaScript output is approximately 228 kB entry + 563 kB App chunk, 791 kB total / 238 kB gzip. The App chunk still exceeds Vite's advisory threshold; no warning is suppressed.

## Acceptance still open

The new checks execute code, actual HTTP requests and React server-rendered recovery markup. They do not control a browser or establish visual/focus behavior. React route/render boundaries compile, but their interactive recovery also needs a browser check.

The prior R1 observation was an API tab blank after an environment restart with concurrent mock/API servers. Its original cause is not established. Mode-specific caches and the new recovery guards are candidate protections; this report does not claim the exact R1 is fixed. Windows Computer Use previously stopped because it could not verify Chrome's URL; no alternative UI automation or further UI input was attempted.

Keep #13 open until real API Dashboard/Analytics/Alerts and configured Journal are reviewed in a browser: selected profile/range, historical day, refresh, request failure, stopped/restarted API, retry, recovery reload and both themes. Keep the full DATA-04/analysis/alert scenario in #21/#22; #14/#15 still return not_implemented until their owners deliver the engines. Do not silently switch API failures to mocks or present a fixture warning as a generated API alert.

Run from frontend: npm run check:views, npm run check, npm run build. From repository root with the backend venv and Node 22.13+: python scripts/check_local_integration.py. See the [integration runbook](../architecture/integration_smoke_test.md) and [current integration report](integration_update_20261115.md).
