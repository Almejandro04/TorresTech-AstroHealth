"""DATA-04 checks: the synthetic 30-day mission generator (no network)."""

import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pytest

import generate_synthetic_mission as generator

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.database.ingestion import Bundle  # noqa: E402  (backend import contract)

READINGS_HEADER = ("astronaut_id,timestamp,mission_day,heart_rate_bpm,spo2_percent,"
                   "respiratory_rate_bpm,measurement_context,source_type,source_id")
JOURNAL_HEADER = ("astronaut_id,timestamp,mission_day,sleep_hours_last_night,mood_score,"
                  "notes,source_type,source_id")


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("synthetic")
    generator.generate(path)
    return path


def hashes(folder: Path) -> dict[str, str]:
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rest(bundle: dict, who: str) -> dict[int, dict]:
    return {r["mission_day"]: r for r in bundle["readings"]
            if r["astronaut_id"] == who and r["measurement_context"] == "rest"}


def test_generation_is_byte_identical(tmp_path: Path, out: Path) -> None:
    generator.generate(tmp_path)
    assert hashes(tmp_path) == hashes(out)
    other = tmp_path / "other_seed"
    generator.generate(other, seed=7)
    assert hashes(other)["readings.csv"] != hashes(out)["readings.csv"]


def test_committed_outputs_match_the_default_generation(out: Path) -> None:
    committed = REPO_ROOT / "data" / "synthetic"
    generated = hashes(out)
    assert {name: digest for name, digest in hashes(committed).items() if name in generated} == generated


def test_every_bundle_passes_the_backend_import_model(out: Path) -> None:
    for path in [out / "mission_ast101_ast102.json", *sorted((out / "fixtures").glob("*.json"))]:
        Bundle.model_validate(load(path))


def test_thirty_days_and_consistent_mission_day(out: Path) -> None:
    bundle = load(out / "mission_ast101_ast102.json")
    assert sorted(rest(bundle, "AST-101")) == list(range(1, 31))
    assert sorted(rest(bundle, "AST-102")) == [1, 2, 3]
    start = date(2026, 11, 1)
    for record in bundle["readings"] + bundle["journal"]:
        observed = date.fromisoformat(record["timestamp"][:10])
        assert record["mission_day"] == (observed - start).days + 1
        assert record["timestamp"].endswith("Z")


def test_provenance_and_ids(out: Path) -> None:
    bundle = load(out / "mission_ast101_ast102.json")
    records = bundle["readings"] + bundle["journal"]
    assert {r["source_type"] for r in records} == {"synthetic"}
    assert {r["source_id"] for r in records} == {"SYN-AH-MISSION-001"}
    assert bundle["source"]["is_clinically_validated"] is False
    ids = {a["astronaut_id"] for a in bundle["astronauts"]}
    assert ids == {"AST-101", "AST-102"} and not ids & {"AST-001", "AST-002"}
    fixture_ids = {load(p)["astronauts"][0]["astronaut_id"] for p in (out / "fixtures").glob("*.json")}
    assert fixture_ids == {"AST-201", "AST-202", "AST-203", "AST-204", "AST-205"}


def test_csv_headers_are_exact(out: Path) -> None:
    assert (out / "readings.csv").read_text(encoding="utf-8").splitlines()[0] == READINGS_HEADER
    assert (out / "journal.csv").read_text(encoding="utf-8").splitlines()[0] == JOURNAL_HEADER
    with (out / "readings.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(load(out / "mission_ast101_ast102.json")["readings"])


def test_scenario_nulls_and_absences(out: Path) -> None:
    bundle = load(out / "mission_ast101_ast102.json")
    series = rest(bundle, "AST-101")
    assert series[12]["heart_rate_bpm"] is None and series[12]["spo2_percent"] is not None
    assert series[13]["respiratory_rate_bpm"] is None
    journal_days = {j["mission_day"] for j in bundle["journal"] if j["astronaut_id"] == "AST-101"}
    assert 14 not in journal_days and len(journal_days) == 29


def test_scenario_values_exercise_the_rule(out: Path) -> None:
    bundle = load(out / "mission_ast101_ast102.json")
    series = rest(bundle, "AST-101")
    baseline = sum(series[d]["heart_rate_bpm"] for d in range(1, 6)) / 5
    threshold = baseline + 5
    elevated = {d for d, r in series.items() if r["heart_rate_bpm"] is not None and r["heart_rate_bpm"] >= threshold}
    assert elevated == {9, 18, 19, 20, 21}
    assert series[22]["heart_rate_bpm"] < threshold
    manifest = load(out / "scenario_manifest.json")["astronauts"]["AST-101"]
    assert manifest["expected_baseline_heart_rate_bpm"] == baseline
    assert manifest["expected_rule"]["detection_day"] == 19


def test_contexts_on_even_days(out: Path) -> None:
    bundle = load(out / "mission_ast101_ast102.json")
    for context, time in (("sleep", "03:00:00Z"), ("exercise", "17:00:00Z")):
        days = {r["mission_day"] for r in bundle["readings"]
                if r["astronaut_id"] == "AST-101" and r["measurement_context"] == context}
        assert days == set(range(2, 31, 2))
        assert all(r["timestamp"].endswith(time) for r in bundle["readings"] if r["measurement_context"] == context)


def test_no_value_is_out_of_shape(out: Path) -> None:
    for path in [out / "mission_ast101_ast102.json", *(out / "fixtures").glob("*.json")]:
        bundle = load(path)
        for r in bundle["readings"]:
            assert any(r[k] is not None for k in ("heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm"))
            assert r["heart_rate_bpm"] is None or r["heart_rate_bpm"] > 0
            assert r["respiratory_rate_bpm"] is None or r["respiratory_rate_bpm"] > 0
            assert r["spo2_percent"] is None or 0 <= r["spo2_percent"] <= 100
        for j in bundle["journal"]:
            assert 0 <= j["sleep_hours_last_night"] <= 24
            assert j["mood_score"] in (1, 2, 3, 4, 5)
