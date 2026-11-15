# AstroHealth continuous integration

Workflow: [.github/workflows/ci.yml](../../.github/workflows/ci.yml).

## Scope

The workflow runs on pushes, pull requests and manual workflow_dispatch. It does not require a PR to integrate; the owner's direct-push workflow is preserved. It is not a branch-protection rule and does not prevent someone with write access from pushing.

| Job | Runtime | Checks |
| --- | --- | --- |
| Frontend | Ubuntu, Node 24 | npm ci, full npm run check, TypeScript and production build |
| Backend and live integration | Ubuntu and Windows, Python 3.13 / Node 24 | pinned pip install, pip check, isolated pytest and the real FastAPI/SQLite replay/restart smoke |

The frontend suite includes contrast, shared mocks, series/defaults, HTTP fixture transport and startup/view/history checks. HTTP fixture tests remain distinct from the real backend smoke. The backend's current four strict xfails are explicitly reported by pytest: two by the documented day-5/day-6 baseline policy difference and two fixtures that show the earlier not-implemented stage. Baselines (#14) and the alert engine (#15) are implemented. Unexpected failures fail the job; no continue-on-error or blanket skips are configured.

The real smoke creates a new temporary SQLite database and owns its loopback server/ports. It checks staged import, idempotence, historical cutoffs, CORS, eight frontend client/history cases and restart persistence, then imports the committed 30-day synthetic mission into a second temporary database and checks baseline, generated alert, resolution, nulls and frontend guards over real HTTP. No working demo database, private records or external biomedical downloads are needed. Browser rendering, keyboard, mobile and actual zoom are not tested by this workflow.

## Permissions and dependency policy

Only contents: read is granted to workflow jobs. Checkout does not persist credentials. No repository secrets, deployments, external messages, pull_request_target event or automatic pushes/merges are used. Official actions are pinned to commit SHAs verified from their v6 refs when this workflow was prepared. npm ci uses the committed lockfile; pip uses the existing pinned requirements. Package caches are selected by those dependency files. Runs for the same ref/PR supersede older runs; other branches are not cancelled.

## Local equivalents

From frontend: npm ci, npm run check, npm run build.

From backend in the configured venv: python -m pip install -r requirements-dev.txt, python -m pip check, python -m pytest -q -rx.

From repository root with that Python and Node 22.13+: python scripts/check_local_integration.py. CI uses Node 24 explicitly.

## Result record

Verified on 2026-11-15: [Actions run 43715674553](https://github.com/Almejandro04/TorresTech-AstroHealth/actions/runs/43715674553) completed successfully on commit `2d64ee0bdd93a3c5103fe4ceaea87a1d2974ca02`, prepared from main `e7fc1a7` on the separate `codex/integration-21-qa-ci-20261115` branch.

| Job | Observed result |
| --- | --- |
| Frontend / Ubuntu | Clean npm ci; all 94 contrast pairs; shared mock fixtures; 9 series/defaults, 15 HTTP-client and 8 startup/view/history checks; TypeScript and production build passed |
| Backend / Ubuntu | pip check passed; 307 passed / 6 expected xfailed; all 8 real frontend-client checks, staged replay/CORS and restart persistence passed |
| Backend / Windows | pip check passed; 307 passed / 6 expected xfailed; all 8 real frontend-client checks, staged replay/CORS and restart persistence passed |

The build retains the visible chunk-size advisory (App chunk 563.47 kB before gzip); no threshold was raised to hide it. At that time the six expected xfails were the then-missing #14/#15 cases and the run covered only the seven-day CORE-01 seed. Since then #14/#15 and DATA-04 have landed: the suite reports 368 passed / 4 strict xfails locally (see [integration results](integration21_results.md)); no newer Actions run is recorded here.

The follow-up commit adds this result record and README links only; it does not change the verified workflow or application source.

The local execution/browser environment became unavailable during this continuation. No new local, keyboard, responsive or 200% zoom results are claimed. Follow the separate [accessibility review plan](accessibility_review.md) once the interactive environment is available.
