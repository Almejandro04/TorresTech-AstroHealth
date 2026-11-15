# AstroHealth frontend — Flight Log

English React/TypeScript prototype for [FRONTEND-01 (#2)](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/2), reviewed in draft PR #24. Flight Log is Claude's implemented design, continued with targeted fixes and verification. The former sidebar/teal scaffold is superseded. See [design rationale and verification](../docs/design/redesign_rationale.md).

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

`check` runs contrast and mock-contract checks. Build includes TypeScript and produces `dist/`; preview uses port 4173. Hash routes support refresh and browser history without server rewrite rules.

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

All reads/writes currently use `mockHealthDataSource` selected explicitly in `src/services/index.ts`. Journal changes last only for the current page session and reset on reload. A mock success never claims server persistence. No live backend integration is delivered here; #13 remains open.

`VITE_API_BASE_URL` defaults to http://localhost:8000. Copy `.env.example` to `.env.local` to configure a future API transport; setting it alone does not activate HTTP reads. The backend must allow the actual frontend origin through CORS when live transport is added.

`src/services/healthDataSource.ts` defines typed reads, filters, cutoff and journal-write behavior. The mock engine derives responses from `docs/examples/mission_seed.json`. `npm run check:mocks` checks the 12 shared response fixtures, journal writes/errors and replay policies. No independent clinical alert engine is introduced.

New journal entries temporarily follow the fixture convention: 08:00 UTC on the selected mission day and source SYN-CORE-001. Corrections keep original timestamp/source. This is a mock integration convention in `journalDefaults.ts`, not a new backend rule; agree effective time/provenance with the backend before live writes.

## Modules

| Path | Responsibility |
| --- | --- |
| src/App.tsx | Data router and fallback routes |
| src/components/AppShell.tsx, MissionBar.tsx | Navigation, theme, mission/profile and replay |
| src/components/MetricChart.tsx, Sparkline.tsx, ui.tsx | Charts, summaries, accessible dialogs and states |
| src/pages/ | Dashboard, Analytics, Alerts and Journal |
| src/hooks/MissionContext.tsx, useResource.ts, useHistory.ts | Shared selection, resource states, stale-result isolation and history |
| src/services/mock/ | Seed-derived engine and explicit demo scenarios |
| src/lib/ | UTC dates, units and display-series helpers |
| src/styles/ | Brand/semantic tokens, base controls, shell and views |
| scripts/ | Contrast and mock-contract checks |

## Review status and remaining work

See the rationale for executed checks and the manual smoke sequence. The production JavaScript bundle is approximately 779 kB / 233 kB gzip; Vite's 500 kB warning is retained. Splitting chart code can be considered later rather than hiding the warning.

The redesign advances mock presentation for #10, #11, #12 and #17; those issues are not automatically complete. Live storage/API, generated alerts, end-to-end testing (#21), and final user design acceptance remain separate. This prototype uses fictional synthetic records and experimental explanations, not medically validated diagnoses or NASA endorsement.
