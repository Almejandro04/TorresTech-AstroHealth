# INTEGRATION-01 (#21) results

Owners: Jorge (@Almejandro04) and Jhonatan (@TheJhonatan144). Procedure:
[integration smoke test](../architecture/integration_smoke_test.md).

## Automated run

| Field | Value |
| --- | --- |
| Date | 2026-11-15 (America/Guayaquil) |
| Base commit | `6d8a58d` (main) plus the working-tree changes of branch `feature/integration-21-e2e` |
| Environment | Windows 11, Python 3.13.3 (`.venv`), Node v24.18.0 |

| Command (from) | Result |
| --- | --- |
| `..\.venv\Scripts\python.exe -m pytest -q -rx` (backend) | 368 passed, 4 strict xfails |
| `..\.venv\Scripts\python.exe -m pip check` (backend) | No broken requirements |
| `.\.venv\Scripts\python.exe -m pytest data\tests -q` (root) | 21 passed |
| `.\.venv\Scripts\python.exe scripts\validate_mission_rules.py` (root) | 10/10 checks passed |
| `.\.venv\Scripts\python.exe scripts\check_local_integration.py` (root), run twice | Passed both times with identical output |

The four xfails: `summary_normal_reference_fixture` and `evaluated_no_active_alerts`
(baseline available from day 6; the fixture shows it at the end of day 5);
`summary_before_analysis_is_implemented` and `alerts_not_implemented_is_not_an_all_clear`
(fixtures of the earlier not-implemented stage).

Before this work, `data\tests` failed one byte-comparison test on Windows because
`core.autocrlf` checked the generated LF files out with CRLF. A `.gitattributes`
(`eol=lf` for `data/synthetic`, `data/processed`, `data/tests/fixtures`) fixes it
without changing any committed content.

### 30-day mission stage (real HTTP, own temporary database and server)

| Step | Observed |
| --- | --- |
| Import `mission_ast101_ast102.json --until-day 30` | Created 1 source, 2 astronauts, 63 readings, 32 journal entries |
| Repeated import | All repeated (0 created, 0 updated) |
| AST-101, end of day 5 | Heart-rate baseline `insufficient_data`; alert evaluation `insufficient_data` |
| AST-101, end of day 9 | Baseline available, 72.2; evaluation `available`; 0 active alerts |
| AST-101, end of day 19 | 1 active `DEMO-HR-CHANGE` alert `ALERT-0001`, warning, window 2026-11-18T12:00:00Z → 2026-11-19T12:00:00Z, observed 80, baseline 72.2, explanation present |
| AST-101, end of day 22 | Same `ALERT-0001`, `resolved`, resolved_at 2026-11-22T12:00:00Z |
| AST-101, end of day 30 (3 queries) | Total 1 each time, same alert ID |
| AST-102 | `insufficient_data` in summary and alerts, empty list |
| Scenario nulls | Day-12 rest heart rate null, day-13 rest respiratory rate null, no day-14 journal |
| Heart-rate card at end of day 12 | 111 beats/min, 2026-11-12T17:00:00Z, context `exercise`, `READING-0024`: the latest non-null value (contract 3.5), not the null rest reading |
| Frontend guards (Node) | 8 views (summary, readings, journal, alerts × days 19 and 22) passed `responses.*` and `matchesView` |

Note: the request to show the day-11 heart rate on the day-12 card does not match
the contract with this scenario. Day 12 is an even day, so its 03:00 sleep and
17:00 exercise readings are later non-null heart rates; the card correctly shows
the latest one with its own time and context.

## Manual rendered checks

| check | expected | actual | evidence | owner | status |
| --- | --- | --- | --- | --- | --- |
| Dashboard AST-101 day 30 with synthetic provenance visible | | | | Jorge | Pending manual run |
| Analytics with gaps on days 12–13 and the reference | | | | Jorge | Pending manual run |
| Mission view day 9 without alert | | | | Jorge | Pending manual run |
| Day 19 alert visible with explanation | | | | Jorge | Pending manual run |
| Day 22 alert resolved | | | | Jorge | Pending manual run |
| AST-102 "More observations needed" | | | | Jorge | Pending manual run |
| API stopped → error state and retry | | | | Jorge | Pending manual run |
| Journal create on AST-101 and sleep refresh | | | | Jorge | Pending manual run |
| Actual 200% zoom on the four views | | | | Jorge | Pending manual run |
| Keyboard navigation | | | | Jorge | Pending manual run |

Use the [clean-start 30-day demo](../architecture/integration_smoke_test.md#clean-start-30-day-demo)
steps. Record observed values only; leave a row pending until it is run.
