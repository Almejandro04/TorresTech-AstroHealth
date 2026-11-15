# Team handoff

State of `main` at `1435cab` (2026-11-15). Every task below comes from an open issue or a pending item recorded in the linked documents.

## By area

| Person | Area | Integrated deliverables | Next tasks (from recorded pending items) |
| --- | --- | --- | --- |
| Jorge — [@Almejandro04](https://github.com/Almejandro04) | Frontend (Flight Log) and team lead; owner of #22, co-owner of #21 | API/data contract v0.1.0 (#1, PR #23); Flight Log views (PR #24); Fetch adapter, acceptance checks and demo runbooks; API/Journal browser acceptance (#13/#17, [browser13_acceptance.md](testing/browser13_acceptance.md)); CI ([ci.md](testing/ci.md)) | Run the 10 "Pending manual run" rows of [integration21_results.md](testing/integration21_results.md) (rendered 30-day views, error/retry, journal, actual 200% zoom, keyboard); the [accessibility checklist](testing/accessibility_review.md); final demo rehearsal (#22) with the [demo runbook](demo_runbook.md) |
| Jhonatan — [@TheJhonatan144](https://github.com/TheJhonatan144) | Backend: API, storage, ingestion, analysis, alerts; co-owner of #21 | FastAPI init (#3) and models/SQLite (#7) (PR #26); REST API (#8, PR #27); import and staged replay (#9, PR #28); baselines (#14, PR #29); alert engine (#15, PR #30); backend tests (#18, PR #31); real-HTTP 30-day integration stage (#21, PR #33) | Contract decisions recorded in [validation_review.md](research/validation_review.md): "Fixture days" explanation wording and the day-5 vs day-6 baseline availability; HTTP exposure of trends only if agreed ([analysis.md](architecture/analysis.md), "Pending: exposing trends over HTTP"); support the manual #21 run |
| Ismael — [@BrandonFreire](https://github.com/BrandonFreire) | Data and research | Indicator dictionary (#4), dataset candidates (#5), BIDMC pipeline (#16), 30-day synthetic generator (#6), data sources (#19), validation review (#20) — integrated in PR #32 ([data_sources.md](data_sources.md)) | Scientific review of the `DEMO-HR-CHANGE` rule (row "Rule DEMO-HR-CHANGE" in [validation_review.md](research/validation_review.md); "DATA-06 will review the evidence later" in [alert_rules.md](architecture/alert_rules.md)) |

## Dependencies

- Jorge's manual #21 checks need the clean-start 30-day demo from [integration_smoke_test.md](architecture/integration_smoke_test.md#clean-start-30-day-demo) (backend commands owned by Jhonatan).
- A change to the explanation wording or to the day-5/day-6 policy is a contract change: it needs the contract document and its fixtures updated in the same change ([api_contract.md](api_contract.md)), with agreement from Jorge (frontend) and Ismael (data).
- Ismael's scientific review may lead to a new rule version; Jhonatan would implement it and Jorge would recheck the rendered alerts.
- The #22 rehearsal depends on the manual #21 rows being recorded.

## Links

[README](../README.md) · [demo runbook](demo_runbook.md) · [#21 results](testing/integration21_results.md) · [integration smoke test](architecture/integration_smoke_test.md) · [validation review](research/validation_review.md) · [data sources](data_sources.md)
