# Accessibility follow-up for INTEGRATION-01 (#21)

## Current evidence boundary

The previously completed [API browser acceptance](browser13_acceptance.md) verifies desktop API views in light/dark, native labeled Journal controls, Enter submission, validation focus, confirmation focus, dirty navigation and API failure/retry. The earlier Flight Log review also records a 375px mock review. Those are focused checks, not a complete assistive-technology or cross-browser certification.

During this continuation the local execution environment became unavailable and the browser-control tool was removed. Therefore no new keyboard, mobile, browser-zoom or assistive-technology observations are marked complete. CI checks code/HTTP behavior and is not a substitute for these rendered checks.

## Next rendered pass

Use a separate checkout/server and disposable mission database from the integration runbook. Keep Flight Log and the contract unchanged. Record commit, browser/version, exact viewport and selected data source/cutoff for every defect.

- [ ] Keyboard-only navigation across all four destinations: Tab/Shift+Tab, Enter, radio arrow keys, native selects, skip link and visible focus. Confirm focus is not trapped outside a modal.
- [ ] Journal invalid/valid inputs, cancel, dirty navigation Keep editing/Discard changes, rejected/unconfirmed writes and retry. Confirm field guidance is associated with inputs and saved/failed feedback receives focus after history refresh.
- [ ] Native dialogs: initial focus, keyboard traversal, Escape and return to invoker. Verify long notes and long alert explanations.
- [ ] Actual browser zoom 200%: verify the browser's displayed zoom setting, then inspect Dashboard, Analytics, Alerts, Journal, controls, dialogs and chart tables in light/dark. Record that setting in evidence. CSS zoom, device-scale emulation and a narrow viewport do not establish actual browser zoom.
- [ ] Responsive widths, including 375px: no document-level horizontal overflow; wide data tables may have their own labeled scroll area. Inspect navigation/feedback, mission controls and Journal mood choices.
- [ ] Screen-reader pass: headings/landmarks, control names, table headers, chart alternatives, unavailable versus empty/error states and live save/error announcements. Record actual reader/browser versions and result; do not infer success from markup alone.
- [ ] A second supported browser: repeat the core read/replay/filter/Journal/failure path and record differences.

## Defect record

| Field | Required evidence |
| --- | --- |
| Trigger | Source/cutoff, route, browser/viewport/zoom and exact keys/actions |
| Expected/actual | Visible behavior, focused element, text announcement or layout measurement |
| Owner/priority | Jorge frontend; link backend/data issues if the defect originates there |
| Correction | Commit and linked issue |
| Retest | Observed result and capture after the fix |

Keep #21 open until its actual DATA-04/analysis/generated-alert flow and remaining browser/accessibility criteria are verified. Do not weaken the criteria to close the issue.
