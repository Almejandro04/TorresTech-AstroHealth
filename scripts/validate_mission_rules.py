"""Validate the synthetic 30-day mission against the real backend (DATA-06).

Run from the repository root (no network):
    .\\.venv\\Scripts\\python.exe scripts\\validate_mission_rules.py

Imports data/synthetic/mission_ast101_ast102.json with the backend CLI into a
temporary database, queries the FastAPI app in-process, checks the experimental
baseline and the DEMO-HR-CHANGE rule, writes data/synthetic/validation_result.json
and exits non-zero if any check fails. The temporary database is deleted.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
DEFAULT_BUNDLE = REPO_ROOT / "data" / "synthetic" / "mission_ast101_ast102.json"
DEFAULT_OUT = REPO_ROOT / "data" / "synthetic" / "validation_result.json"
AST = "/api/astronauts/AST-101"
FORBIDDEN = ("diagnos", "disease", "treat", "prescrib", "medication", "cardiac arrest",
             "arrhythmia", "hypoxia diagnosis")
EXPERIMENTAL_MARKERS = ("controlled example", "not a validated")


def end_of_day(day: int) -> str:
    return f"2026-11-{day:02d}T23:59:59Z"


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def validate(bundle_path: Path) -> dict:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    rest = {r["mission_day"]: r for r in bundle["readings"]
            if r["astronaut_id"] == "AST-101" and r["measurement_context"] == "rest"}
    window = [r for r in bundle["readings"] if r["astronaut_id"] == "AST-101" and r["mission_day"] <= 5]
    baseline = mean([rest[d]["heart_rate_bpm"] for d in range(1, 6)])
    mixed = mean([r["heart_rate_bpm"] for r in window if r["heart_rate_bpm"] is not None])

    checks: list[dict] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="astrohealth-validate-") as tmp:
        db = Path(tmp) / "mission.db"
        env = {**os.environ, "ASTROHEALTH_DB_PATH": str(db)}
        imported = subprocess.run(
            [sys.executable, "-m", "app.database", "import-json", str(bundle_path), "--until-day", "30"],
            cwd=BACKEND, env=env, capture_output=True, text=True,
        )
        report = json.loads(imported.stdout) if imported.returncode == 0 else {}
        check("import_committed", imported.returncode == 0 and report.get("committed") is True,
              report.get("records") or imported.stderr.strip())
        if imported.returncode != 0:
            return {"bundle": str(bundle_path.relative_to(REPO_ROOT)), "passed": False, "checks": checks}

        os.environ["ASTROHEALTH_DB_PATH"] = str(db)
        sys.path.insert(0, str(BACKEND))
        from fastapi.testclient import TestClient  # noqa: PLC0415  (after sys.path)

        from app.database import connect, repository  # noqa: PLC0415
        from app.main import create_app  # noqa: PLC0415

        with TestClient(create_app()) as client:
            def summary(profile: str, as_of: str | None = None) -> dict:
                return client.get(f"{profile}/summary", params={"as_of": as_of} if as_of else None).json()

            def alerts(profile: str, as_of: str | None = None) -> dict:
                return client.get(f"{profile}/alerts", params={"as_of": as_of} if as_of else None).json()

            day5 = summary(AST, end_of_day(5))["data"]["baselines"]["heart_rate_bpm"]
            check("baseline_unavailable_until_day_5", day5["status"] == "insufficient_data",
                  {"status": day5["status"], "sample_count": day5["sample_count"]})

            day6 = summary(AST, "2026-11-06T00:00:00Z")["data"]["baselines"]["heart_rate_bpm"]
            check("baseline_available_from_day_6_matches_hand_mean",
                  day6["status"] == "available" and day6["sample_count"] == 5
                  and abs(day6["value"] - baseline) < 1e-9,
                  {"status": day6["status"], "api_value": day6["value"], "hand_mean": baseline,
                   "sample_count": day6["sample_count"], "context": day6["measurement_context"]})

            check("exercise_and_sleep_excluded_from_baseline",
                  day6["measurement_context"] == "rest" and abs(day6["value"] - mixed) > 1e-9,
                  {"rest_only_mean": baseline, "mean_if_contexts_were_mixed": mixed})

            day9 = alerts(AST, end_of_day(9))
            active9 = [a for a in day9["data"] if a["status"] == "active"]
            check("isolated_spike_day_9_no_alert",
                  day9["meta"]["evaluation_status"] == "available" and not active9,
                  {"evaluation_status": day9["meta"]["evaluation_status"], "active_alerts": len(active9)})

            day19 = alerts(AST, end_of_day(19))
            active19 = [a for a in day19["data"] if a["status"] == "active"]
            alert = active19[0] if len(active19) == 1 else {}
            expected_observed = mean([rest[18]["heart_rate_bpm"], rest[19]["heart_rate_bpm"]])
            check("sustained_change_day_19_one_warning",
                  len(active19) == 1
                  and alert.get("rule_id") == "DEMO-HR-CHANGE" and alert.get("rule_version") == "fixture-1"
                  and alert.get("severity") == "warning"
                  and alert.get("window_start") == rest[18]["timestamp"]
                  and alert.get("window_end") == rest[19]["timestamp"]
                  and abs(alert.get("observed_value", float("nan")) - expected_observed) < 1e-9
                  and abs(alert.get("baseline_value", float("nan")) - baseline) < 1e-9,
                  {key: alert.get(key) for key in ("alert_id", "rule_id", "rule_version", "severity",
                                                   "mission_day", "window_start", "window_end",
                                                   "observed_value", "baseline_value")}
                  | {"expected_observed_value": expected_observed, "active_alerts": len(active19)})

            day22 = alerts(AST, end_of_day(22))["data"]
            check("resolved_on_day_22",
                  len(day22) == 1 and day22[0]["status"] == "resolved"
                  and day22[0]["resolved_at"] == rest[22]["timestamp"],
                  {"alerts": len(day22), "status": day22[0]["status"] if day22 else None,
                   "resolved_at": day22[0]["resolved_at"] if day22 else None})

            views = [alerts(AST, end_of_day(25)) for _ in range(3)]
            with closing(connect(db)) as conn:
                stored = len(repository.list_alerts(conn, "AST-101"))
            ids = {a["alert_id"] for view in views for a in view["data"]}
            check("no_duplicates_after_three_evaluations",
                  all(view["meta"]["total"] == 1 for view in views) and len(ids) == 1 and stored == 1,
                  {"totals": [view["meta"]["total"] for view in views], "alert_ids": sorted(ids),
                   "stored_alerts": stored})

            short = summary("/api/astronauts/AST-102")["data"]["alert_summary"]
            short_alerts = alerts("/api/astronauts/AST-102")
            check("ast102_insufficient_data_never_all_clear",
                  short["evaluation_status"] == "insufficient_data" and short["active_count"] is None
                  and short_alerts["meta"]["evaluation_status"] == "insufficient_data"
                  and short_alerts["data"] == [],
                  {"summary": short["evaluation_status"], "alerts": short_alerts["meta"]["evaluation_status"]})

            text = f"{alert.get('description', '')} {alert.get('explanation', '')}".lower()
            found = [word for word in FORBIDDEN if word in text]
            check("alert_text_is_observational_and_experimental",
                  bool(alert) and not found and all(marker in text for marker in EXPERIMENTAL_MARKERS),
                  {"forbidden_found": found, "description": alert.get("description"),
                   "explanation": alert.get("explanation")})

    return {
        "bundle": str(bundle_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "baseline_heart_rate_bpm": baseline,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result = validate(args.bundle.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    for item in result["checks"]:
        print(f"{'PASS' if item['passed'] else 'FAIL'}  {item['name']}")
    print("All checks passed." if result["passed"] else "Some checks failed.")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
