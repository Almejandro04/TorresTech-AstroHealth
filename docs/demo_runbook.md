# AstroHealth demonstration runbook

## Scope and reproducibility

There are two explicit rehearsals: the **frontend mock demonstration** below, and **real persisted API monitoring** using the seven-day contract seed. FastAPI/SQLite transport, staged replay and journal persistence pass the isolated smoke. The current API browser workflow is verified; see the acceptance record. Calculated baselines and generated alerts remain #14/#15; DATA-04 generation remains #6.

A clean checkout, npm ci and npm run dev in frontend suffice. With no local override the source is mock. If a local API override exists, deliberately set VITE_DATA_SOURCE=mock and restart Vite. The UI must show Synthetic demo. Do not use the HTTP test fixture as evidence that the team's backend is complete.

## Reset / preflight

1. Run npm run check and npm run build in frontend.
2. Start Vite on an unoccupied loopback port. Open /#/dashboard; choose Demo Astronaut 1 / AST-001.
3. Reload to reset session journal data and switches. Confirm seven observed days and 30 planned days.
4. Open Synthetic demo and leave Contract fixtures / Normal / Succeeds selected. Presentation samples are optional extra layout examples, not generated scientific findings.
5. Keep a copy of docs/examples/mission_seed.json and api_examples.json available. The committed Flight Log captures are an illustration if browser presentation fails, not proof of a running backend.

## Approximately two-minute presentation

| Step | Action | Explain |
| --- | --- | --- |
| 1 — identity | Dashboard; point to fictional astronaut, mission day and Synthetic demo | This is an educational monitoring prototype with synthetic observations. |
| 2 — reference | Choose Mission view Day 5 | Days 1–5 are the fixture's reference period. The experimental fixture evaluation has no active alert at this cutoff. This does not prove good health. |
| 3 — introduced change | Return to latest Day 7 | The latest resting heart rate is 84 beats/min, oxygen 97%, sleep 5.5 hours and mood 2/5. Respiratory rate retains its Day 6 observation because Day 7 is null. |
| 4 — history | Open Analytics; choose 3 days | Dates, units and references stay explicit. Respiratory data has a gap on Day 7. Show the data table for an accessible equivalent. |
| 5 — explanation | Open Alerts and the shared warning | Fixture days 6–7 have a resting mean of 81 versus reference 72. Read the explanation, evidence window and rule/source; do not describe this as a clinical threshold or diagnosis. |
| 6 — user control | Journal; edit a note; Cancel, then save a changed note | Cancel restores the previous entry. A confirmed mock save preserves its daily ID and lasts only for this page session. |

For a shorter demo, omit the journal step. It is P1 and does not block the core reference/change/alert demonstration.

## Failure / empty-state rehearsal

- Day 3: insufficient history, no misleading all-clear.
- AST-002: no observations, not zero-valued health.
- Day 7 respiratory history: null remains a chart gap despite a retained earlier dashboard snapshot.
- Demo scenarios -> Analysis not implemented: unavailable analysis differs from evaluated no alerts.
- Demo scenarios -> Requests fail: display failure and recovery, not a silent switch of data source.
- Next journal save -> Rejected field / Connection failure / Unconfirmed: preserve input, explain uncertainty and retry. Settings apply once. Reset with Reload or Restore seed data.
- Navigate away from a dirty journal: Keep editing preserves input; Discard changes is explicit.

## Real API rehearsal — monitoring and persistence

1. Follow the root README setup. Use a NEW disposable database, exact CORS origins and the existing import CLI; keep the absolute database path available to both terminals.
2. Run the automatic smoke first from the repository root: `.\.venv\Scripts\python.exe scripts\check_local_integration.py`. It creates its own independent database/server; passing it does not seed the interactive database.
3. In the interactive backend terminal, import the CORE-01 seed through day 3 and start FastAPI. Enable API mode in the frontend, with the configured API base URL and explicit journal manifest/time. Restart Vite. The mission bar must identify API synthetic data.
4. Confirm AST-001/day 3 against the API summary. AST-002 must remain an empty profile. Analysis and alert evaluation must show unavailable, not evaluated-no-alerts or a healthy result.
5. In another backend terminal configured with the SAME absolute database path, import through day 5, then choose Refresh data in Flight Log. Verify the new latest day and chart/table observations without losing the selected profile/range. Import through day 7 to show the missing respiratory value and retained earlier dashboard timestamp.
6. For historical replay, select day 3 in Flight Log. For direct API consumers, pass the import report's `post_import.cutoffs[astronaut_id]` as `as_of`; `latest_stored_cutoffs` reports physical storage separately. Importing backwards does not delete future rows or set a global API clock.
7. Create/correct a daily Journal entry with the imported source and effective time. Compare its stable ID, summary and sleep history. Restart FastAPI using the same database, reload and verify persistence. A mock save is session-only; an API save is stored in SQLite.
8. Stop/restart the API and test visible errors/retry, then keyboard and actual 200% zoom. Repeat these browser actions for future changes; the current API review is recorded separately from the CLI. Actual 200% zoom and broader assistive/cross-browser checks remain pending.

The current transport/persistence and rendered API/Journal subset is verified in [browser acceptance](testing/browser13_acceptance.md); the supported R1 restart recheck passed. The full DATA-04/actual-engine rehearsal remains #21/#22. Use the explicitly labeled mock fallback for the illustrative baseline/alert explanation until #14/#15 are integrated. Never present the mock warning as a generated API alert.
