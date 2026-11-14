# AstroHealth usability requirements

Contract version: **0.1.0**  
Tracking: [CORE-01 / #1](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/1)  
Interface language: **English**, confirmed in the working session.

This is the interaction specification accompanying [the API/data contract](api_contract.md). It supplies acceptance scenarios for future frontend work. There is no implemented interface or completed usability evaluation in this change.

## 1. Principles used

The following short mapping credits [Jakob Nielsen's ten usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/). The AstroHealth requirements are our proposed application of those principles.

| Reference | Focus | AstroHealth application |
| --- | --- | --- |
| H1 | State feedback | Distinguish loading, saved, failed, missing observations, and unavailable analysis. |
| H2 | Familiar meaning | Display human labels, explicit units, mission days, and observation times. |
| H3 | User control | Allow journal correction and cancellation of unsaved edits. |
| H4 | Consistent conventions | Reuse navigation, metric names, severity cues, and action labels. |
| H5 | Prevent mistakes | Constrain inputs and prevent duplicate saves while submitting. |
| H6 | Visible choices | Label mood options; prefill the selected day's existing journal. |
| H7 | Efficient interaction | Preserve selected astronaut/range and support keyboard operation. |
| H8 | Focused content | Prioritize indicators; reveal evidence in alert details. |
| H9 | Recoverable errors | Explain corrections, preserve entered values, and offer retry. |
| H10 | Context help | Explain baselines, synthetic provenance, and incomplete analysis beside their use. |

Selected [Laws of UX](https://lawsofux.com/) inform additional design choices:

| Reference | AstroHealth implementation requirement |
| --- | --- |
| [Fitts](https://lawsofux.com/fittss-law/) | Provide distinct, adequately sized and spaced action targets near the form. Verify pointer and keyboard operation. |
| [Hick](https://lawsofux.com/hicks-law/) | Keep the four MVP views and one main form action; defer fatigue and advanced alert controls. |
| [Jakob](https://lawsofux.com/jakobs-law/) | Use familiar navigation, labeled inputs, Save changes, Cancel, and standard chart controls. |
| [Proximity](https://lawsofux.com/law-of-proximity/) | Keep a metric's value, unit, timestamp, context, and provenance together. |
| [Von Restorff](https://lawsofux.com/von-restorff-effect/) | Reserve emphasis for important alert states, with readable text/icons in addition to color. |

These are design references, not a claim that following a checklist proves usability or aerospace certification. The detailed scenarios below are project-specific acceptance requirements.

## 2. Confirmed product decisions

| Decision | Required behavior |
| --- | --- |
| Journal can be corrected | Load an existing day, edit it, and explicitly save an update to the same entry ID. |
| Latest value is per indicator | Cards consume `summary.latest_metrics`; each value retains its own observation day/time. |
| Alerts are consultative | Users inspect explanations; the engine owns active/resolved state. No acknowledge or manual-resolve action. |
| Mood is 1-5 | Five labeled choices: Very low, Low, Neutral, High, Very high. No preselected score on a new day. |
| Fatigue is deferred | Initial journal fields are sleep, mood, and notes. No fatigue input, API field, or score. |
| Interface is English | Navigation, labels, help, validation feedback, and recovery actions use English. |

Unspecified spacing, icon choice, and other routine presentation details remain Jorge's implementation choices. New persistent state, new user actions, or changes to metric meaning require a contract decision before implementation.

## 3. Observable acceptance scenarios

### UX-01: Metric values retain their own observation times

Applies to FRONTEND-02 / #10 and FRONTEND-06 / #13. References: H1, H2, Proximity.

- Given the latest raw reading on day 7 has no respiratory rate, but day 6 has 16 breaths/min, the respiratory card shows 16 with day 6's time. The heart-rate card can simultaneously show day 7's value and time.
- Render `latest_metrics.<indicator>.value`, `.unit`, `.timestamp`, and `.mission_day` together. Do not substitute the summary day or a neighboring card's time for an older observation.
- If a metric has never been observed, show "Not recorded" and its known unit; do not display zero or a healthy-state cue.
- Display the original context when relevant and an explicit synthetic-demo/source cue. An older value remains distinguishable from a newly measured one without inventing a clinical freshness threshold.
- Chart history preserves the original null/gap. A prior value on a card does not create another chart point.

### UX-02: Daily journal correction and cancellation

Applies to FRONTEND-05 / #17, BACKEND-03 / #8, and FRONTEND-06 / #13. References: H3, H5, H6, H9.

- Selecting a day with an existing entry prefills sleep, mood, and notes. Display the selected day/profile and label the save action "Save changes".
- A new entry has no assumed mood or sleep value. Display the five mood labels, the sleep unit (hours), and optionality explicitly.
- Cancel discards the unsaved draft and restores the last loaded values without making a write request. It does not undo an already completed save.
- Disable repeated submission while a save is pending and show "Saving...". Only a successful 200/201 response produces "Journal saved".
- A successful edit retains the journal ID and the single-entry-per-day rule. Refresh summary/history/alerts after the response using the selected observation cutoff.
- A rejected request keeps the draft and shows field-specific guidance. A network failure keeps the draft and offers "Try again" without showing success.
- Leaving or switching the profile/day with unsaved edits offers a clear keep-editing/discard choice; no warning is required when the form is unchanged.
- Before editing a past day or exiting historical replay, make the target day/cutoff explicit. Do not silently write a different day or relabel historical values as live.

### UX-03: Understandable alerts and honest availability

Applies to FRONTEND-04 / #12 and FRONTEND-06 / #13. References: H1, H4, H8, H10, Von Restorff.

- Every alert detail exposes indicator, attention level, observation time, status, description, explanation, and supporting rule/reference data.
- Distinguish severity using text and an icon as well as color. No clinical diagnosis, treatment instruction, flashing decoration, or unsupported "All healthy" summary is added.
- `evaluation_status=not_implemented` displays "Analysis not available"; `insufficient_data` displays "More observations needed".
- Only an available evaluation with no active alerts may display "No active alerts detected in the evaluated data". It never substitutes for missing or failed analysis.
- No button lets a user resolve, acknowledge, hide, or delete the detected condition. Future interaction changes require a separate decision and API update.

### UX-04: Validation and recovery feedback

Applies to FRONTEND-05 / #17 and FRONTEND-06 / #13. References: H4, H5, H9.

- Label fields and match `error.code` / `details[].field` to plain English feedback. Example: "Enter a mood score from 1 to 5." Do not expose stack traces or require interpreting codes such as `VALIDATION_ERROR`.
- Keep the user's entered values after field, server, or connection errors. Allow correction/retry and distinguish an unknown profile from an empty history.
- Unknown results stay unknown: an API error is not zero observations, a null value is not zero, and an empty alert list without evaluation is not a normal-health result.
- A timeout may leave write success uncertain. Explain that uncertainty and use the contract's retry identity rather than claiming the save definitely failed or creating a duplicate entry.

### UX-05: Consistent, focused navigation and charts

Applies to FRONTEND-01 / #2, FRONTEND-03 / #11, and FRONTEND-06 / #13. References: H4, H7, H8, Fitts, Hick, Jakob.

- Use Dashboard, Analytics, Alerts, and Journal consistently; visibly identify the active view.
- Keep chosen astronaut and mission range visible and stable during refresh/navigation where those selections apply.
- Use labeled controls, a visible keyboard focus, adequate target spacing, and a predictable tab order. Required actions cannot depend on hover alone.
- Charts show metric units, selected period, and any available comparable baseline; no-history and insufficient-baseline states remain distinct.
- Test a narrow viewport and a desktop viewport. Verify the primary save/cancel and chart-selection actions are reachable without overlapping controls.

## 4. Validation responsibilities

The contract preparation checks JSON/CSV syntax, per-indicator timestamps, provenance, and request/response invariants. It does not execute any of the UI scenarios above.

Jorge verifies the relevant scenarios in frontend pull requests; Jhonatan verifies supporting API behavior; Ismael checks unit/provenance interpretation. The shared end-to-end issue #21 verifies the supported demo path after implementation. Record observed results or defects there rather than marking these requirements passed before a UI exists.
