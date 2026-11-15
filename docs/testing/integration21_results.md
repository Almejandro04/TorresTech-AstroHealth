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

Run on 2026-11-15 by Jhonatan (@TheJhonatan144) on Windows in a Chromium-based browser (Brave), API mode, with a disposable database containing the CORE-01 seed and the 30-day synthetic mission.

| check | expected | actual | evidence | owner | status |
| --- | --- | --- | --- | --- | --- |
| Dashboard AST-101 day 30 with synthetic provenance visible | API · SYNTHETIC MISSION DATA label; per-indicator time and provenance | Label shown; every card shows SYN-AH-MISSION-001 and its record ID; exercise values marked "Not compared" against the rest reference | [01_dashboard_ast101_day30.png](integration21/01_dashboard_ast101_day30.png) | Jhonatan | Pass |
| Mission view day 5 without reference | No reference before day 6; no all-clear | "More observations needed (5 so far)" on every indicator; Attention says "This is not an all-clear" | [02_day5_no_reference.png](integration21/02_day5_no_reference.png) | Jhonatan | Pass |
| Mission view day 9 without alert (isolated spike) | Rest HR elevated, no alert | Rest HR 84, +11.8 vs reference 72.2; Alerts: "No active alerts detected in the evaluated data", described as not a statement about health | [03_day9_spike_dashboard.png](integration21/03_day9_spike_dashboard.png), [04_day9_no_alerts.png](integration21/04_day9_no_alerts.png) | Jhonatan | Pass |
| Analytics with gaps on days 12–13 and the reference | Gaps kept, never 0; reference visible | Day-12 rest HR has no point; "No value recorded: Day 13. The gap is kept, not filled."; references 72.2 / 97.6 / 15.6 drawn | [05_day14_analytics_gaps.png](integration21/05_day14_analytics_gaps.png) | Jhonatan | Pass |
| Day 19 alert visible with explanation | 1 active warning, window days 18–19 | Warning · Active; observed 80, reference 72.2, difference +7.8; window Day 18 12:00 → Day 19 12:00 UTC; explanation shown (begins with "Fixture days", known limitation) | [06_day19_alert_active.png](integration21/06_day19_alert_active.png) | Jhonatan | Pass |
| Day 22 alert resolved | Same alert resolved | 0 active · 1 resolved; the same alert shown as Resolved | [07_day22_alert_resolved.png](integration21/07_day22_alert_resolved.png) | Jhonatan | Pass |
| AST-102 "More observations needed" | Insufficient history, no all-clear | "More observations needed (3 so far)" on Dashboard; Alerts shows "More observations needed" | [08_ast102_insufficient.png](integration21/08_ast102_insufficient.png), [16_zoom200_alerts.png](integration21/16_zoom200_alerts.png) | Jhonatan | Pass |
| API stopped → error state and retry | Error distinct from an empty history; recovery after retry | "Could not load the mission profiles", stating it is different from having no observations, with Try again; after restarting Uvicorn the data returned, including the saved journal change | [12_api_stopped.png](integration21/12_api_stopped.png), [13_api_recovered.png](integration21/13_api_recovered.png) | Jhonatan | Pass |
| Journal save and sleep refresh | Saved entry keeps its ID; charts refresh | Correction of AST-102 day 3 (sleep 7 h, Neutral, note): "Journal saved", ID unchanged (JOURNAL-0039); Analytics and Dashboard show 7 h. Performed as a correction of an existing day, not a new-day create | [09_journal_saved.png](integration21/09_journal_saved.png), [10_ast102_sleep_refreshed.png](integration21/10_ast102_sleep_refreshed.png) | Jhonatan | Pass |
| Actual 200% zoom on the four views | Readable and usable | Dashboard, Analytics, Alerts and Journal readable when zoomed; header controls reflow and the timeline moves to its own row | [14_zoom200_dashboard.png](integration21/14_zoom200_dashboard.png), [15_zoom200_analytics.png](integration21/15_zoom200_analytics.png), [16_zoom200_alerts.png](integration21/16_zoom200_alerts.png), [17_zoom200_journal.png](integration21/17_zoom200_journal.png), [18_zoom_analytics_period.png](integration21/18_zoom_analytics_period.png) | Jhonatan | Pass (visual; zoom level set in the browser, not measured by tooling) |
| Keyboard navigation | Visible focus on controls | Visible focus outline on the Dashboard tab after keyboard navigation | [11_keyboard_focus_dashboard.png](integration21/11_keyboard_focus_dashboard.png) | Jhonatan | Pass (partial: focus visibility observed; full tab-order audit not recorded) |

Notes:
- The journal check modified the demo database (AST-102 day 3). Recreate a fresh database
  with the clean-start steps before presenting.
- Known limitation: the alert explanation begins with "Fixture days" because the rule
  template matches the contract fixture `explainable_synthetic_alert`.
- Not covered: screen-reader and cross-browser review (one Chromium-based browser only).
- No P0 integration defect was observed in the supported demo path.

Use the [clean-start 30-day demo](../architecture/integration_smoke_test.md#clean-start-30-day-demo)
steps. Record observed values only; leave a row pending until it is run.
