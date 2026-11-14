# AstroHealth frontend

React + TypeScript application shell for [FRONTEND-01 / #2](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/2). The interface is English, with a light workspace, dark-blue navigation, and teal accents selected during the working session.

## What this initial setup includes

- Four navigable views: Dashboard, Analytics, Alerts, and Journal, plus an unknown-route recovery page.
- A shared responsive shell with visible active navigation, mission context, synthetic-demo identification, keyboard focus, and a skip-to-content link.
- A typed, asynchronous mock data source using the approved v0.1.0 profile/summary fixtures. No backend or external dataset is needed to run the application.
- React, TypeScript, Vite, Tailwind CSS, Lucide React, React Router, and Recharts, with exact direct dependency versions and a committed npm lockfile.
- Loading, error, and retry handling for the shared mission-context loader.

The views deliberately identify their content as in preparation. Full dashboard indicator cards, charts, alert presentation, the journal form, and live API integration belong to FRONTEND-02/03/04/05/06. Installed Recharts is ready for the chart issue; no charts are implemented here.

## Prerequisites and install

Use Node.js 22.12 or newer supported by the declared engine range, and npm. `package.json` records the npm version used for this setup. Work from the repository checkout containing this frontend branch.

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173** or the equivalent **http://127.0.0.1:5173** loopback URL printed by Vite. Port 5173 is fixed: stop another process using it rather than silently switching ports.

The default route is `/#/dashboard`. Hash routing makes refresh and browser Back/Forward work without requiring deployment-server route rewrites. There is no login requirement for the fictional demo.

## Configuration

No environment file is needed for mock development. The prepared API base defaults to `http://localhost:8000`.

To set a different base locally:

```powershell
Copy-Item .env.example .env.local
```

Edit `VITE_API_BASE_URL` in `.env.local` and restart Vite. Use only the service origin/base, without a query, fragment, or the `/api` endpoint suffix. `buildApiUrl('/api/health')` appends that endpoint. Vite client environment values are public application configuration.

Setting a base URL **does not enable live API calls**. The data source is explicitly mocked in `src/services/index.ts`; it never silently substitutes mock results after a real API failure. FRONTEND-06 will implement the same `HealthDataSource` interface using Fetch/Axios and switch this export. Local backend CORS must allow the actual frontend origin (`localhost:5173` and/or `127.0.0.1:5173`) used by the browser.

## Verify and build

```powershell
npm run typecheck
npm run build
npm run preview
```

- `typecheck` checks TypeScript without generating JavaScript.
- `build` includes the type check and creates the production bundle in `dist/`.
- `preview` serves that built bundle at **http://localhost:4173** (equivalent loopback IP: `127.0.0.1:4173`).

Vite's development server transpiles TypeScript; use the explicit type check/build before opening a pull request. `node_modules/`, `dist/`, local environment files, and tool caches are not committed.

## Module ownership and extension points

| Path | Responsibility |
| --- | --- |
| `src/App.tsx` | Routes and fallback navigation |
| `src/components/AppShell.tsx` | Shared navigation, page header, mission context, and accessibility behavior |
| `src/components/SectionPlaceholder.tsx` | Reusable initial view placeholder |
| `src/pages/` | Independent view modules to replace in their corresponding issues |
| `src/types/health.ts` | Astronaut, readings, journal, alerts, snapshots, baseline, summary, and response types |
| `src/services/healthDataSource.ts` | Transport-independent `HealthDataSource` interface |
| `src/services/mockHealthDataSource.ts` | Deterministic asynchronous mock reads; cloned objects prevent accidental shared-fixture mutation |
| `src/services/mock/fixtures.ts` | Small typed copies of shared contract examples |
| `src/services/index.ts` | Explicit data-source selection boundary |
| `src/services/config.ts` | API base configuration and endpoint URL builder |
| `src/hooks/useMissionData.ts` | Mission-profile loading, cancellation of stale results, and retry state |
| `src/styles.css` | Tailwind import and shared responsive shell styles |
| `public/favicon.svg` | Local brand asset; no network resource is needed |

Create additional hooks/assets/components only when used. The initial fixture type declarations are checked using TypeScript `satisfies`, rather than casting arbitrary JSON to a response type. `HealthDataSource` currently needs only `getAstronauts` and `getSummary`; add other contract methods in the feature/integration issues as they become necessary.

## Contract and mock maintenance

- [Approved API/data contract](../docs/api_contract.md)
- [Usability requirements](../docs/ux_requirements.md)
- [Shared API examples](../docs/examples/api_examples.json)

`src/services/mock/fixtures.ts` copies the bodies of these shared cases:

1. `fictional_profiles`
2. `summary_introduced_change_and_missing_metric`
3. `summary_profile_without_observations`

The initial shell loads the first fictional profile. The mock source also supports the second profile's empty summary, and rejects unknown profile IDs. When the contract changes, update the shared examples, these typed fixtures, and the consumers together.

The contract's dashboard snapshots preserve the last non-null observation independently per indicator. For example, the summary fixture's day-7 raw reading has no respiratory value, while `latest_metrics.respiratory_rate_bpm` retains 16 breaths/min with the actual day-6 timestamp. Future dashboard cards consume those snapshots and retain the date; charts must keep the original gap.

## Manual smoke checks

1. Start the app with the backend stopped; confirm the fictional profile and mission day load from mocks.
2. Visit all four navigation links. Confirm the URL, active item, heading, and browser title change.
3. Refresh a non-default route and use browser Back/Forward. Confirm the selected view remains coherent.
4. Visit `/#/missing` and use the dashboard recovery link.
5. Check desktop and a 375px-wide viewport: no horizontal overflow, overlapping actions, or missing navigation.
6. Use Tab/Shift+Tab and the skip link. Confirm focus is visible and the page heading receives focus on route changes.
7. Confirm the synthetic-demo label is visible and no placeholder claims that analysis found the astronaut healthy.
8. Run the production build and repeat a navigation smoke check using `npm run preview`.

This setup does not claim completed usability evaluation of the future monitoring features. Their acceptance scenarios remain in the linked usability specification and integration issue.

## Implementation references

- [Vite setup](https://vite.dev/guide/)
- [Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite)
- [Lucide React](https://lucide.dev/guide/react)
- [Recharts installation](https://recharts.github.io/en-US/guide/installation/)
