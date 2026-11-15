# AstroHealth frontend — Flight Log

English React/TypeScript prototype for [FRONTEND-01 (#2)](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/2), integrated through PR #24. Flight Log is Claude's implemented design, continued with targeted fixes and verification. The former sidebar/teal scaffold is superseded. See [design rationale and verification](../docs/design/redesign_rationale.md).

## Run locally

Use Node.js satisfying `^20.19.0 || >=22.12.0` and npm (the lockfile was generated with npm 11.12.1).

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173/#/dashboard (or the localhost URL printed by Vite). Port 5173 is strict; do not stop another teammate's server without checking ownership. For a separate review server: `npm run dev -- --port 5174`.

```powershell
npm run typecheck
npm run check
npm run build
npm run preview
```

`check` runs contrast, mock-contract, series/component edge-case and HTTP-client checks. Build includes TypeScript and produces `dist/`; preview uses port 4173. Hash routes support refresh and browser history without server rewrite rules.

## Implemented experience

- NASA Blue masthead with four destinations; mobile bottom navigation; visible focus and skip link.
- User-selected light/dark theme, light by default, remembered locally when storage is available. Public Sans and DM Mono are self-hosted.
- Mission/profile context and a 30-day planned timeline. The approved seed provides seven observed days for AST-001; the timeline does not invent the remaining observations. AST-002 demonstrates empty history.
- Dashboard: latest non-null indicator snapshots with their own timestamp, context, unit and provenance. A retained Day 6 respiratory value does not fill the Day 7 chart gap.
- Analytics: period selection, comparable reference, missing-data gaps, point-in-time readings separate from daily journals, and keyboard-accessible data-table disclosure.
- Alerts: list/detail, evidence, source and engine-owned status. No acknowledge/resolve action. Extra severity/status examples are explicitly labeled Presentation sample.
- Journal: create/correct one daily entry, validation, cancellation, unsaved-navigation confirmation, disabled controls while saving, and recoverable rejected/unconfirmed writes.
- Synthetic demo dialog: analysis unavailable, slow/failed reads, rejected/disconnected/unconfirmed writes, and seed reset.

## Data and integration boundary

The default source is mock. Set VITE_DATA_SOURCE=api in .env.local and restart Vite to use createApiHealthDataSource. VITE_API_BASE_URL defaults to http://localhost:8000 and VITE_API_TIMEOUT_MS defaults to 10000. Invalid configuration fails explicitly; the real client never falls back to mock responses. API mode is identified in the mission bar. The backend must allow the exact frontend origin/port through CORS.

The Fetch adapter implements profiles, summary, vital/journal histories, alert filters and journal writes. It checks supported v0.1.0 wire shapes, profile identity and observation cutoffs, and normalizes HTTP/network/timeout failures. A lost write response is unconfirmed, never a promise that nothing was sent. Corrections must retain daily identity. Refresh data on Dashboard/Analytics/Alerts reloads resources without changing URL selections.

Mock journal changes last only for the current page session and reset on reload. New mock entries retain the fixture convention 08:00 UTC / SYN-CORE-001. API creates instead require explicit VITE_JOURNAL_SOURCE_ID and VITE_JOURNAL_TIME_UTC (HH:MM:SS), matching the imported mission and agreed effective observation time; otherwise new creates stay disabled with an explanation. Existing corrections preserve their original source/time.

The backend now serves persisted profiles, readings, journal, summary and alerts, plus JSON/CSV import and staged days. The unchanged Fetch client passes seven real FastAPI/SQLite checks, including journal create/correct/retry and history refresh; restart persistence is verified. Run the root scripts/check_local_integration.py for an isolated repeatable smoke. #13/#17 remain open for rendered API workflow acceptance; #14/#15 still return explicit not_implemented analysis/alerts. The read-only check:health still proves only service health.

The mock engine derives its data from docs/examples/mission_seed.json. npm run check:mocks verifies the shared examples and replay policies. scripts/fixture-api.mjs and serve-fixture-api.mjs are explicitly test-only HTTP shims for checking the transport, not the backend deliverable or a second production API.

See [the root README](../README.md), [demo runbook](../docs/demo_runbook.md) and [integration procedure](../docs/architecture/integration_smoke_test.md) for supported commands, scopes and blockers.

## Modules

| Path | Responsibility |
| --- | --- |
| src/App.tsx | Data router and fallback routes |
| src/components/AppShell.tsx, MissionBar.tsx | Navigation, theme, mission/profile and replay |
| src/components/MetricChart.tsx, Sparkline.tsx, ui.tsx | Charts, summaries, accessible dialogs and states |
| src/pages/ | Dashboard, Analytics, Alerts and Journal |
| src/hooks/MissionContext.tsx, useResource.ts, useHistory.ts | Shared selection, resource states, stale-result isolation and history |
| src/services/apiHealthDataSource.ts, responseValidation.ts | Fetch transport, wire guards and error normalization |
| src/services/mock/ | Seed-derived engine and explicit demo scenarios |
| src/lib/ | UTC dates, units and display-series helpers |
| src/styles/ | Brand/semantic tokens, base controls, shell and views |
| scripts/ | Contrast, mock/series/HTTP checks, real health probe and test-only HTTP fixture |

## Review status and remaining work

See the rationale for executed checks and the manual smoke sequence. The production JavaScript bundle is approximately 787 kB / 236 kB gzip; Vite's 500 kB warning is retained. Splitting chart code can be considered later rather than hiding the warning.

Functional acceptance evidence for #10/#11/#12 is in [frontend_acceptance.md](../docs/testing/frontend_acceptance.md). Real HTTP storage and journal persistence are verified; API browser completion, generated alerts and full end-to-end testing (#21) remain separate. See the [current integration update](../docs/testing/integration_update_20261115.md). This prototype uses fictional synthetic records and experimental explanations, not medically validated diagnoses or NASA endorsement.
