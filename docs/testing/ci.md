# AstroHealth continuous integration

Workflow: [.github/workflows/ci.yml](../../.github/workflows/ci.yml).

## Scope

The workflow runs on pushes, pull requests and manual workflow_dispatch. It does not require a PR to integrate; the owner's direct-push workflow is preserved. It is not a branch-protection rule and does not prevent someone with write access from pushing.

| Job | Runtime | Checks |
| --- | --- | --- |
| Frontend | Ubuntu, Node 24 | npm ci, full npm run check, TypeScript and production build |
| Backend and live integration | Ubuntu and Windows, Python 3.13 / Node 24 | pinned pip install, pip check, isolated pytest and the real FastAPI/SQLite replay/restart smoke |

The frontend suite includes contrast, shared mocks, series/defaults, HTTP fixture transport and startup/view/history checks. HTTP fixture tests remain distinct from the real backend smoke. The backend's current six expected analysis/alert xfails are explicitly reported by pytest; they are not completed #14/#15 functionality. Unexpected failures fail the job; no continue-on-error or blanket skips are configured.

The real smoke creates a new temporary SQLite database and owns its loopback server/ports. It checks staged import, idempotence, historical cutoffs, CORS, eight frontend client/history cases and restart persistence. No working demo database, private records or external biomedical downloads are needed. Browser rendering, keyboard, mobile and actual zoom are not tested by this workflow.

## Permissions and dependency policy

Only contents: read is granted to workflow jobs. Checkout does not persist credentials. No repository secrets, deployments, external messages, pull_request_target event or automatic pushes/merges are used. Official actions are pinned to commit SHAs verified from their v6 refs when this workflow was prepared. npm ci uses the committed lockfile; pip uses the existing pinned requirements. Package caches are selected by those dependency files. Runs for the same ref/PR supersede older runs; other branches are not cancelled.

## Local equivalents

From frontend: npm ci, npm run check, npm run build.

From backend in the configured venv: python -m pip install -r requirements-dev.txt, python -m pip check, python -m pytest -q -rx.

From repository root with that Python and Node 22.13+: python scripts/check_local_integration.py. CI uses Node 24 explicitly.

## Result record

The first workflow run must be inspected before calling CI verified or integrating the workflow into main. Initial branch publication is a validation step, not a passing result. This document will be updated with the actual run result.

The local execution/browser environment became unavailable during this continuation. No new local, keyboard, responsive or 200% zoom results are claimed. Follow the separate [accessibility review plan](accessibility_review.md) once the interactive environment is available.
