"""Versioned alert rule configuration (BACKEND-05 / #15).

One synthetic-scenario rule. Its threshold and persistence are a SIMULATION
ASSUMPTION for the demo: they do not come from clinical sources or NASA and
are not validated criteria for astronauts. See docs/architecture/alert_rules.md.
"""

RULE_ID = "DEMO-HR-CHANGE"
RULE_VERSION = "fixture-1"
INDICATOR = "heart_rate_bpm"
UNIT = "beats/min"
CONTEXT = "rest"

# Each of two consecutive mission days after the reference window must have a
# resting daily mean >= baseline + DELTA_BPM. One elevated day never triggers.
DELTA_BPM = 5.0
CONSECUTIVE_DAYS = 2
SEVERITY = "warning"

DESCRIPTION = "Introduced synthetic resting heart-rate change."
EXPLANATION = (
    "Fixture days {first_day}-{last_day} have a resting mean of {observed} beats/min; "
    "the synthetic days {ref_first}-{ref_last} reference mean is {baseline}. "
    "This controlled example illustrates explanation fields, not a validated medical threshold."
)
