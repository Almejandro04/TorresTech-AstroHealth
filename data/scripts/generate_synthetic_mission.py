"""Generate the reproducible 30-day synthetic AstroHealth mission (DATA-04).

Run from the repository root (no network):
    .\\.venv\\Scripts\\python.exe data\\scripts\\generate_synthetic_mission.py [--seed 2026]

Every value is synthetic. Reference values are [SIMULATION-ASSUMPTION]s chosen
inside published ranges (see data/synthetic/README.md); the scenario changes
are introduced on purpose to exercise the experimental baseline and the
DEMO-HR-CHANGE rule. Nothing here is a validated physiological model.

The same arguments always produce byte-identical files.
"""

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

GENERATOR = "data/scripts/generate_synthetic_mission.py"
GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "0.1.0"
SOURCE_ID = "SYN-AH-MISSION-001"
SOURCE_TYPE = "synthetic"
MISSION_DAYS = 30
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "data" / "synthetic"

READING_FIELDS = ["astronaut_id", "timestamp", "mission_day", "heart_rate_bpm", "spo2_percent",
                  "respiratory_rate_bpm", "measurement_context", "source_type", "source_id"]
JOURNAL_FIELDS = ["astronaut_id", "timestamp", "mission_day", "sleep_hours_last_night", "mood_score",
                  "notes", "source_type", "source_id"]

REST_TIME, SLEEP_TIME, EXERCISE_TIME, JOURNAL_TIME = "12:00:00", "03:00:00", "17:00:00", "08:00:00"

# AST-101 scenario (mission days).
REFERENCE_DAYS = range(1, 6)
SPIKE_DAY = 9
MISSING_HR_DAY = 12
MISSING_RR_DAY = 13
MISSING_JOURNAL_DAY = 14
SUSTAINED_DAYS = range(18, 22)
RETURN_DAY = 22
LOW_SLEEP_MOOD_DAYS = range(18, 24)

LIMITATIONS = (
    "Synthetic fictional mission. Values are simulation assumptions chosen inside published "
    "ranges and introduced changes; not a validated physiological model, not astronaut data "
    "and not clinically validated."
)


def astronaut(number: int) -> dict:
    return {
        "astronaut_id": f"AST-{number}",
        "name": f"Demo Astronaut {number}",
        "is_fictional": True,
        "mission_start_date": None,  # set by build()
        "planned_duration_days": MISSION_DAYS,
    }


class Mission:
    def __init__(self, start: date) -> None:
        self.start = start
        self.readings: list[dict] = []
        self.journal: list[dict] = []

    def stamp(self, day: int, time: str) -> str:
        return f"{(self.start + timedelta(days=day - 1)).isoformat()}T{time}Z"

    def reading(self, who: str, day: int, time: str, context: str,
                hr: int | None, spo2: int | None, rr: int | None) -> None:
        self.readings.append({
            "astronaut_id": who, "timestamp": self.stamp(day, time), "mission_day": day,
            "heart_rate_bpm": hr, "spo2_percent": spo2, "respiratory_rate_bpm": rr,
            "measurement_context": context, "source_type": SOURCE_TYPE, "source_id": SOURCE_ID,
        })

    def entry(self, who: str, day: int, sleep: float, mood: int) -> None:
        self.journal.append({
            "astronaut_id": who, "timestamp": self.stamp(day, JOURNAL_TIME), "mission_day": day,
            "sleep_hours_last_night": sleep, "mood_score": mood, "notes": None,
            "source_type": SOURCE_TYPE, "source_id": SOURCE_ID,
        })


def source(seed: int, start: date) -> dict:
    return {
        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "description": "Synthetic 30-day AstroHealth mission for fictional astronauts; not real astronaut or patient observations.",
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "command": f"python {GENERATOR} --seed {seed} --start-date {start.isoformat()}",
        "seed": seed,
        "schema_version": SCHEMA_VERSION,
        "scenario": "AST-101: stable days 1-5, isolated spike day 9, missing values days 12-14, sustained resting heart-rate change days 18-21, return day 22, recovery days 24-30. AST-102: days 1-3 only.",
        "limitations": LIMITATIONS,
        "is_clinically_validated": False,
        "planned_mission_days": MISSION_DAYS,
    }


def daily_vitals(rng: random.Random, mission: Mission, who: str, day: int) -> None:
    """Sleep and exercise readings on even days, to show context separation."""
    if day % 2 == 0:
        mission.reading(who, day, SLEEP_TIME, "sleep", 56 + rng.randint(-1, 1), 97, 14)
        mission.reading(who, day, EXERCISE_TIME, "exercise", 110 + rng.randint(-3, 3), 97, 22)


def normal_sleep(rng: random.Random) -> float:
    return 6.5 + rng.choice([-0.25, 0.0, 0.25])


def normal_mood(rng: random.Random) -> int:
    return 3 if rng.random() < 0.2 else 4


def build_ast101(rng: random.Random, mission: Mission) -> dict:
    who = "AST-101"
    reference_hr = []
    baseline = None
    for day in range(1, MISSION_DAYS + 1):
        if day in REFERENCE_DAYS:
            hr = 72 + rng.randint(-1, 1)
            reference_hr.append(hr)
            if day == REFERENCE_DAYS.stop - 1:
                baseline = round(sum(reference_hr) / len(reference_hr))
        elif day == SPIKE_DAY:
            hr = baseline + 12
        elif day == MISSING_HR_DAY:
            hr = None
        elif day in SUSTAINED_DAYS:
            hr = baseline + 8 + rng.randint(-1, 1)
        elif day == RETURN_DAY:
            hr = baseline + rng.randint(-1, 0)
        else:
            hr = baseline + rng.randint(-1, 1)
        spo2 = 97 if day in LOW_SLEEP_MOOD_DAYS else 98 + rng.choice([-1, 0])
        rr = None if day == MISSING_RR_DAY else 15 + rng.randint(-1, 1)
        mission.reading(who, day, REST_TIME, "rest", hr, spo2, rr)
        daily_vitals(rng, mission, who, day)
        if day == MISSING_JOURNAL_DAY:
            continue
        if day in LOW_SLEEP_MOOD_DAYS:
            mission.entry(who, day, rng.choice([5.0, 5.25, 5.5]), 2)
        else:
            mission.entry(who, day, normal_sleep(rng), normal_mood(rng))
    return {"reference_heart_rate_bpm": reference_hr, "rounded_reference_heart_rate_bpm": baseline}


def build_ast102(rng: random.Random, mission: Mission) -> None:
    who = "AST-102"
    for day in range(1, 4):
        mission.reading(who, day, REST_TIME, "rest", 72 + rng.randint(-1, 1),
                        98 + rng.choice([-1, 0]), 15 + rng.randint(-1, 1))
        mission.entry(who, day, normal_sleep(rng), normal_mood(rng))


def fixture(start: date, number: int, days: int, hr: dict[int, int | None] | None = None,
            rr: dict[int, int | None] | None = None, skip_journal: tuple[int, ...] = ()) -> tuple[dict, Mission]:
    """A small deterministic scenario with resting readings only (no noise)."""
    mission = Mission(start)
    who = f"AST-{number}"
    for day in range(1, days + 1):
        mission.reading(who, day, REST_TIME, "rest", (hr or {}).get(day, 70), 98, (rr or {}).get(day, 15))
        if day not in skip_journal:
            mission.entry(who, day, 6.5, 4)
    profile = {**astronaut(number), "mission_start_date": start.isoformat()}
    return profile, mission


def bundle(seed: int, start: date, profiles: list[dict], mission: Mission) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": source(seed, start),
        "astronauts": profiles,
        "readings": mission.readings,
        "journal": mission.journal,
    }


def write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, records: list[dict], fields: list[str], integers: list[str]) -> None:
    frame = pd.DataFrame(records, columns=fields)
    for name in integers:
        frame[name] = frame[name].astype("Int64")
    frame.to_csv(path, index=False, lineterminator="\n")


def generate(out: Path, seed: int = 2026, start: date = date(2026, 11, 1)) -> dict:
    rng = random.Random(seed)
    mission = Mission(start)
    reference = build_ast101(rng, mission)
    build_ast102(rng, mission)
    profiles = [{**astronaut(n), "mission_start_date": start.isoformat()} for n in (101, 102)]

    main_bundle = bundle(seed, start, profiles, mission)
    write_json(out / "mission_ast101_ast102.json", main_bundle)
    write_json(out / "mission_manifest.json",
               {k: main_bundle[k] for k in ("schema_version", "source", "astronauts")})
    write_csv(out / "readings.csv", mission.readings, READING_FIELDS,
              ["mission_day", "heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm"])
    write_csv(out / "journal.csv", mission.journal, JOURNAL_FIELDS, ["mission_day", "mood_score"])

    rest_hr = reference["reference_heart_rate_bpm"]
    write_json(out / "scenario_manifest.json", {
        "source_id": SOURCE_ID,
        "seed": seed,
        "mission_start_date": start.isoformat(),
        "label": "[SIMULATION-ASSUMPTION]",
        "astronauts": {
            "AST-101": {
                "reference_days": [REFERENCE_DAYS.start, REFERENCE_DAYS.stop - 1],
                "reference_rest_heart_rate_bpm": rest_hr,
                "expected_baseline_heart_rate_bpm": sum(rest_hr) / len(rest_hr),
                "scenario_base_heart_rate_bpm": reference["rounded_reference_heart_rate_bpm"],
                "days": {
                    "1-5": "Stable reference: rest HR 72 +/- 1, SpO2 97-98, RR 15 +/- 1, sleep 6.25-6.75 h, mood 3-4.",
                    "9": "Isolated spike: rest HR = scenario base + 12 on this day only.",
                    "12": "Rest heart_rate_bpm is null (SpO2 and RR present).",
                    "13": "Rest respiratory_rate_bpm is null.",
                    "14": "No journal entry (absence, not 0).",
                    "18-21": "Sustained change: rest HR = scenario base + 8 (+/- 1).",
                    "22": "Rest HR returns to the scenario base (-1..0).",
                    "18-23": "Sleep 5.0-5.5 h, mood 2, rest SpO2 97 (artificial pattern; no causal claim).",
                    "24-30": "Recovery toward the reference.",
                    "even days": "Additional sleep (03:00Z) and exercise (17:00Z) readings.",
                },
                "expected_rule": {
                    "rule_id": "DEMO-HR-CHANGE",
                    "rule_version": "fixture-1",
                    "baseline_available_from_day": 6,
                    "no_alert_at_day": 9,
                    "detection_day": 19,
                    "window_days": [18, 19],
                    "severity": "warning",
                    "resolution_day": 22,
                },
            },
            "AST-102": {"days": "1-3 only", "expected_evaluation_status": "insufficient_data"},
        },
    })

    fixtures = {
        "normal.json": fixture(start, 201, 8),
        "sustained_deviation.json": fixture(start, 202, 8, hr={6: 78, 7: 78}),
        "isolated_spike.json": fixture(start, 203, 8, hr={7: 82}),
        "missing_values.json": fixture(start, 204, 8, hr={6: None}, rr={7: None}, skip_journal=(8,)),
        "insufficient_history.json": fixture(start, 205, 3),
    }
    for name, (profile, small) in fixtures.items():
        write_json(out / "fixtures" / name, bundle(seed, start, [profile], small))
    return main_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 11, 1))
    args = parser.parse_args(argv)
    result = generate(args.out, args.seed, args.start_date)
    print(f"Wrote {len(result['readings'])} readings and {len(result['journal'])} journal entries to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
