# AstroHealth demonstration runbook

## Scope and reproducibility

The supported rehearsal is the **frontend mock demonstration** from the committed contract seed. FastAPI currently serves only health. This is not a claim of Dataset -> SQLite -> API -> UI integration. Use the integration runbook for that later path.

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

## Backend connection rehearsal — blocked until available

1. Check the current backend issue/README commands rather than inventing a generator or database reset command.
2. Generate/import the agreed synthetic mission, retain its manifest and record the actual backend-generated record IDs.
3. Start FastAPI and configure exact frontend CORS. Run npm run check:health -- http://127.0.0.1:8000.
4. Enable VITE_DATA_SOURCE=api, configure the base URL, and restart Vite. The UI must identify API synthetic data.
5. Follow docs/architecture/integration_smoke_test.md for persisted values, analysis, safe replay and journal writes.
6. Only claim end-to-end completion once these values survive backend restart and the actual ingestion/rule flow is verified.

Missing backend/data commands are tracked by #7/#8/#9/#6/#14/#15. The outline and mock fallback are ready; the final integrated rehearsal remains open in #21 and #22.
