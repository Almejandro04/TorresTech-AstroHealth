"""DATA-03 checks: BIDMC normalization over an invented offline fixture.

No network. Expected counts were worked out by hand from the fixture
(see fixtures/README.md).
"""

import json
import math
import shutil
from pathlib import Path

import pandas as pd
import pytest

import acquire_bidmc
import normalize_bidmc

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def result(tmp_path: Path) -> dict:
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(FIXTURES / "bidmc_99_Numerics.csv", raw)
    out = tmp_path / "out"
    normalized = normalize_bidmc.normalize(raw, out)
    return {"out": out, **normalized}


def test_mapping_identity_and_no_mission_columns(result: dict) -> None:
    windows = pd.read_csv(result["out"] / "numerics_1min.csv")
    assert {"heart_rate_bpm", "pulse_rate_bpm", "respiratory_rate_bpm", "spo2_percent"} <= set(windows.columns)
    assert not {"timestamp", "mission_day", "astronaut_id"} & set(windows.columns)
    assert set(windows["subject_id"]) == {"bidmc:99"}
    assert set(windows["source_type"]) == {"terrestrial_biomedical"}
    assert set(windows["source_id"]) == {"PHYSIONET-BIDMC-1.0.0"}
    assert set(windows["measurement_context"]) == {"unknown"}


def test_quality_report_counts(result: dict) -> None:
    quality = json.loads((result["out"] / "quality_report.json").read_text(encoding="utf-8"))
    subject = quality["subjects"]["bidmc:99"]

    # 130 seconds plus one duplicated second.
    assert subject["rows_read"] == 131
    assert subject["rows_rejected"] == {"invalid_time": 0, "duplicate_elapsed_s": 1, "no_values": 1}
    assert subject["rows_accepted"] == 129
    assert subject["shape_failures_set_null"] == {
        "heart_rate_bpm": 1, "pulse_rate_bpm": 0, "respiratory_rate_bpm": 0, "spo2_percent": 1,
    }
    # PULSE: 5 NaN (t=10..14). SpO2: 1 shape failure + 35 NaN (t=60..94).
    assert subject["null_values_in_accepted_rows"] == {
        "heart_rate_bpm": 1, "pulse_rate_bpm": 5, "respiratory_rate_bpm": 0, "spo2_percent": 36,
    }
    assert subject["windows_generated"] == 3
    assert subject["windows_with_all_variables_null"] == 1
    assert quality["totals"]["rows_accepted"] == 129


def test_window_medians_and_minimum_valid_seconds(result: dict) -> None:
    windows = result["windows"].set_index("window_index")

    # Window 0: HR is 70 x29 (t=5 nulled) and 80 x30 -> the 30th of 59 values is 80.
    first = windows.loc[0]
    assert (first["heart_rate_bpm"], first["n_valid_heart_rate_bpm"]) == (80, 59)
    assert (first["pulse_rate_bpm"], first["n_valid_pulse_rate_bpm"]) == (72, 55)
    assert (first["respiratory_rate_bpm"], first["n_valid_respiratory_rate_bpm"]) == (16, 60)
    assert (first["spo2_percent"], first["n_valid_spo2_percent"]) == (98, 59)

    # Window 1: SpO2 has 24 valid seconds (< 30) -> null; t=100 was rejected.
    second = windows.loc[1]
    assert (second["heart_rate_bpm"], second["n_valid_heart_rate_bpm"]) == (75, 59)
    assert math.isnan(second["spo2_percent"]) and second["n_valid_spo2_percent"] == 24

    # Window 2: 10 seconds only -> every variable is null, counts are kept.
    third = windows.loc[2]
    assert all(math.isnan(third[name]) for name in normalize_bidmc.VARIABLES)
    assert third["n_valid_heart_rate_bpm"] == 10
    assert (third["window_start_elapsed_s"], third["window_end_elapsed_s"]) == (120, 180)


def test_nulls_are_empty_cells_in_the_csv(result: dict) -> None:
    lines = (result["out"] / "numerics_1min.csv").read_text(encoding="utf-8").splitlines()
    row_1 = lines[2].split(",")
    assert row_1[10] == "" and row_1[11] == "24"  # spo2_percent, n_valid_spo2_percent
    assert "NaN" not in "\n".join(lines) and "nan" not in "\n".join(lines)


def test_manifest_keeps_provenance_and_policies(result: dict) -> None:
    manifest = json.loads((result["out"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["license"].startswith("Open Data Commons Attribution")
    assert manifest["doi"] == "10.13026/C2208R"
    assert len(manifest["citations"]) == 3
    assert manifest["subjects"] == {"bidmc:99": {"age": "not parsed", "sex": "not parsed"}}
    assert manifest["inputs"][0]["file"] == "bidmc_99_Numerics.csv"
    assert "No UTC timestamps" in manifest["timebase_policy"]


def test_output_is_deterministic(tmp_path: Path, result: dict) -> None:
    again = tmp_path / "again"
    normalize_bidmc.normalize(result["out"].parent / "raw", again)
    for name in ("numerics_1min.csv", "manifest.json", "quality_report.json"):
        assert (again / name).read_bytes() == (result["out"] / name).read_bytes()


def test_wrong_header_and_missing_input_fail(tmp_path: Path) -> None:
    with pytest.raises(normalize_bidmc.NormalizationError):
        normalize_bidmc.normalize(tmp_path, tmp_path / "out")
    (tmp_path / "bidmc_98_Numerics.csv").write_text("Time, HR\n0,70\n", encoding="utf-8")
    with pytest.raises(normalize_bidmc.NormalizationError):
        normalize_bidmc.normalize(tmp_path, tmp_path / "out")


def test_fix_metadata_parsing(tmp_path: Path) -> None:
    fix = tmp_path / "bidmc_99_Fix.txt"
    fix.write_text("bidmc_99\nAge: 50\nGender: F\n", encoding="utf-8")
    assert normalize_bidmc.read_subject_metadata(fix) == {"age": 50, "sex": "F"}
    fix.write_text("no metadata\n", encoding="utf-8")
    assert normalize_bidmc.read_subject_metadata(fix) == {"age": "not parsed", "sex": "not parsed"}


def test_checksum_lookup_by_suffix_without_network() -> None:
    sums = acquire_bidmc.parse_checksums("abc  bidmc_csv/bidmc_01_Numerics.csv\ndef  README\n")
    assert acquire_bidmc.expected_hash(sums, "bidmc_01_Numerics.csv") == ("bidmc_csv/bidmc_01_Numerics.csv", "abc")
    with pytest.raises(acquire_bidmc.AcquisitionError):
        acquire_bidmc.expected_hash(sums, "bidmc_02_Numerics.csv")


def test_acquisition_without_network_fails_clearly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def offline(url: str) -> bytes:
        raise acquire_bidmc.AcquisitionError(f"Could not download {url}: offline")

    monkeypatch.setattr(acquire_bidmc, "fetch", offline)
    assert acquire_bidmc.main(["--out", str(tmp_path / "raw")]) != 0
