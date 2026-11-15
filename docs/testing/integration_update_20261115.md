# Integration update — 2026-11-15

## Delivered and integrated scope

The review started from main 6964d199a7bfbf959fb1818f8bc9af73ff8addf0 after backend PRs #26/#27/#28. Work uses a separate checkout and the branch codex/ingestion-cutoff-and-integration-20261115. Flight Log, the v0.1.0 HTTP contract, shared data fixtures, teammate assignments and other worktrees are preserved.

### #9 correction

Commit [9e94071](https://github.com/Almejandro04/TorresTech-AstroHealth/commit/9e940719870c1526c12ce8e171ea7b03135381ab) fixes an observed future-data handoff: importing through day 5 then requesting day 3 used to report day-5 cutoffs for future analysis consumers. The report now separates selected-view post_import.cutoffs from physical latest_stored_cutoffs. No stored records are deleted. Regression checks cover JSON and CSV, historical summary/readings/journal, exact fractions and unchanged stored rows.

#9 was reopened with Jhonatan still assigned because DATA-04 validation and actual analysis/alert reevaluation are not delivered. No generated 30-day dataset or empty evaluation callback is substituted for those dependencies.

### Our integration/documentation issues

- #13: the unchanged frontend Fetch client is now checked against actual FastAPI/SQLite, not only a fixture HTTP server. Profiles, snapshots, history/pagination/cutoffs, empty profile, unavailable analysis, 404/422, journal upsert and reading conflicts pass.
- #17: a real journal create/correct/retry retains one daily ID, preserves zero sleep, appears in API history/summary and survives a backend restart. Rendered configured-create/error/focus/refresh acceptance still needs review.
- #21: scripts/check_local_integration.py automates a new task-owned temporary database and loopback server, staged import, idempotence, backward replay, explicit CORS, the existing seven-check client probe, shutdown/restart and persistence. It cleans up its own resources and never resets the working database. The script is run from the repository root with the configured venv Python and Node 22.13+.
- #22: root/frontend READMEs, demo and integration runbook now describe available storage/routes/import commands, exact setup/configuration and distinct mock versus API behavior. No claim is made that pending analysis generates the fixture warning.

## Executed checks

| Check | Result |
| --- | --- |
| Backend pytest | 307 passed, 6 expected #14/#15 xfails |
| pip check | No broken requirements |
| New real integration smoke | Passed: day 3 -> 5 -> 7, stable IDs, no duplicate replay, historical cutoff, CORS, seven real Fetch checks, restart persistence |
| Clean npm ci | 87 packages installed |
| npm run check | Passed: 94 contrast pairs, shared mocks, 9 series/default checks, 15 HTTP-fixture client checks |
| npm run build | Passed, including TypeScript |
| API-mode production build | Passed in separate temporary output |
| Browser UI review | Not performed in this continuation; R1 remains open |

Verification environment: Windows, Python 3.14.5, Node 25.9.0 and npm 11.12.1. The frontend bundle remains approximately 787 kB / 236 kB gzip; Vite's 500 kB advisory is not hidden. Generated build/environment/database artifacts are not committed.

## Remaining acceptance

| Issue | Status after this work | Still required |
| --- | --- | --- |
| #9 | Reopened; temporal handoff corrected | DATA-04 import and real analysis/alert handoff after #14/#15 |
| #13 | Open; real transport/storage checks passed | Rendered dashboard/charts/range/refresh/API-stop recovery, R1 recheck |
| #17 | Open; real journal persistence passed | Rendered configured create/correct/rejected/uncertain retry, focus and dependent-view refresh |
| #21 | Open; repeatable real smoke delivered | DATA-04 -> analysis -> alerts -> UI, actual 200% zoom and broader assistive/cross-browser review |
| #22 | Open; current README/demo instructions delivered | Final integrated rehearsal and scientific source/license/scenario links when delivered |

R1 is the prior API tab blank after an environment restart with concurrent mock/API dev modes. Mode-specific Vite caches are present, but that proposed correction has not been rendered-retested. Windows Computer Use previously stopped because it could not verify Chrome's URL; no alternative UI automation or new browser claim is made here. See the [exact record](../architecture/integration_smoke_test.md#r1--api-review-reload-became-blank).

Next: repeat the interactive sequence in [the runbook](../architecture/integration_smoke_test.md), then use Ismael's actual export from #6 and Jhonatan's #14/#15 implementations when they land. Fetch main and preserve concurrent changes before every integration. A passing health request or HTTP fixture is not end-to-end acceptance.
