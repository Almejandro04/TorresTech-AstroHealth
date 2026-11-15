"""Normalize the downloaded BIDMC numerics into 1-minute windows (Pandas).

Run from the repository root after acquire_bidmc.py:
    .\\.venv\\Scripts\\python.exe data\\scripts\\normalize_bidmc.py

Input:  data/raw/bidmc/bidmc_##_Numerics.csv (+ bidmc_##_Fix.txt, acquisition.json)
Output: data/processed/bidmc_subset/numerics_1min.csv, manifest.json, quality_report.json

Policy (see data/README.md):
- These are terrestrial ICU patients. Rows keep `subject_id = "bidmc:##"`,
  `source_type = "terrestrial_biomedical"` and are never astronaut records.
- The timebase is elapsed seconds from the start of each recording. No UTC
  timestamp and no mission day are created: the source's dates are shifted
  by de-identification and are not real.
- `measurement_context = "unknown"`: an ICU bedside monitor in a
  non-standardized situation, not a protocol resting measurement.
- Shape failures (HR, PULSE or RESP <= 0; SpO2 outside 0-100) become null and
  are counted. They are data-shape failures, not clinical outliers.
- Each 60 s window reports the median of each variable and its count of valid
  seconds; with fewer than 30 valid seconds the variable is null there.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

SCRIPT_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "bidmc"
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "bidmc_subset"

SOURCE_ID = "PHYSIONET-BIDMC-1.0.0"
SOURCE_TYPE = "terrestrial_biomedical"
MEASUREMENT_CONTEXT = "unknown"
HEADER = ["Time [s]", "HR", "PULSE", "RESP", "SpO2"]
COLUMNS = {
    "HR": "heart_rate_bpm",
    "PULSE": "pulse_rate_bpm",
    "RESP": "respiratory_rate_bpm",
    "SpO2": "spo2_percent",
}
VARIABLES = list(COLUMNS.values())
MISSING_TOKENS = {"", "NaN", "nan", "NA"}
NUMERICS_RE = re.compile(r"bidmc_(\d{2})_Numerics\.csv")


class NormalizationError(ValueError):
    """The input cannot be normalized as documented."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_subject_metadata(fix_path: Path) -> dict:
    """Age and sex from bidmc_##_Fix.txt, or "not parsed"."""
    if not fix_path.exists():
        return {"age": "not parsed", "sex": "not parsed"}
    text = fix_path.read_text(encoding="utf-8", errors="replace")
    age = re.search(r"^Age:\s*(\d+)\s*$", text, re.MULTILINE)
    sex = re.search(r"^(?:Gender|Sex):\s*([A-Za-z]+)\s*$", text, re.MULTILINE)
    return {
        "age": int(age.group(1)) if age else "not parsed",
        "sex": sex.group(1) if sex else "not parsed",
    }


def clean_subject(path: Path, subject_id: str) -> tuple[pd.DataFrame, dict]:
    """Per-second rows of one subject plus its quality counts."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
    raw.columns = [column.strip() for column in raw.columns]
    if list(raw.columns) != HEADER:
        raise NormalizationError(f"{path.name}: header must be {', '.join(HEADER)}")

    quality = {
        "rows_read": len(raw),
        "rows_rejected": {"invalid_time": 0, "duplicate_elapsed_s": 0, "no_values": 0},
        "unparseable_values_set_null": dict.fromkeys(VARIABLES, 0),
        "shape_failures_set_null": dict.fromkeys(VARIABLES, 0),
    }

    time = pd.to_numeric(raw["Time [s]"].str.strip(), errors="coerce")
    valid_time = time.notna() & (time >= 0) & (time == time.round())
    quality["rows_rejected"]["invalid_time"] = int((~valid_time).sum())
    raw, time = raw[valid_time], time[valid_time]

    frame = pd.DataFrame({"subject_id": subject_id, "elapsed_s": time.astype("int64")})
    for column, name in COLUMNS.items():
        text = raw[column].str.strip()
        values = pd.to_numeric(text, errors="coerce")
        quality["unparseable_values_set_null"][name] = int((values.isna() & ~text.isin(MISSING_TOKENS)).sum())
        frame[name] = values.astype("float64")

    duplicated = frame.duplicated(subset=["subject_id", "elapsed_s"], keep="first")
    quality["rows_rejected"]["duplicate_elapsed_s"] = int(duplicated.sum())
    frame = frame[~duplicated]

    for name in ("heart_rate_bpm", "pulse_rate_bpm", "respiratory_rate_bpm"):
        bad = frame[name] <= 0
        quality["shape_failures_set_null"][name] = int(bad.sum())
        frame.loc[bad, name] = float("nan")
    bad = (frame["spo2_percent"] < 0) | (frame["spo2_percent"] > 100)
    quality["shape_failures_set_null"]["spo2_percent"] = int(bad.sum())
    frame.loc[bad, "spo2_percent"] = float("nan")

    empty = frame[VARIABLES].isna().all(axis=1)
    quality["rows_rejected"]["no_values"] = int(empty.sum())
    frame = frame[~empty].sort_values("elapsed_s").reset_index(drop=True)

    quality["rows_accepted"] = len(frame)
    quality["null_values_in_accepted_rows"] = {name: int(frame[name].isna().sum()) for name in VARIABLES}
    return frame, quality


def to_windows(frame: pd.DataFrame, window_s: int, min_valid_s: int) -> pd.DataFrame:
    """Median per variable per window; null when fewer than min_valid_s valid seconds."""
    rows = []
    for (subject_id, index), group in frame.groupby(
        [frame["subject_id"], frame["elapsed_s"] // window_s], sort=True
    ):
        row = {
            "subject_id": subject_id,
            "window_index": int(index),
            "window_start_elapsed_s": int(index) * window_s,
            "window_end_elapsed_s": (int(index) + 1) * window_s,
        }
        for name in VARIABLES:
            valid = group[name].dropna()
            row[name] = float(valid.median()) if len(valid) >= min_valid_s else None
            row[f"n_valid_{name}"] = int(len(valid))
        row["measurement_context"] = MEASUREMENT_CONTEXT
        row["source_type"] = SOURCE_TYPE
        row["source_id"] = SOURCE_ID
        rows.append(row)

    columns = ["subject_id", "window_index", "window_start_elapsed_s", "window_end_elapsed_s"]
    for name in VARIABLES:
        columns += [name, f"n_valid_{name}"]
    columns += ["measurement_context", "source_type", "source_id"]
    windows = pd.DataFrame(rows, columns=columns)
    for name in VARIABLES:
        windows[name] = windows[name].astype("float64")
    return windows


def normalize(raw_dir: Path, out_dir: Path, window_s: int = 60, min_valid_s: int = 30) -> dict:
    inputs = sorted(path for path in raw_dir.glob("bidmc_*_Numerics.csv") if NUMERICS_RE.fullmatch(path.name))
    if not inputs:
        raise NormalizationError(f"No bidmc_##_Numerics.csv in {raw_dir}; run acquire_bidmc.py first.")

    acquisition_file = raw_dir / "acquisition.json"
    acquisition = json.loads(acquisition_file.read_text(encoding="utf-8")) if acquisition_file.exists() else None
    acquired = {entry["file"]: entry["sha256"] for entry in (acquisition or {}).get("files", [])}

    frames, subjects, input_files = [], {}, []
    quality = {"subjects": {}}
    for path in inputs:
        number = NUMERICS_RE.fullmatch(path.name).group(1)
        subject_id = f"bidmc:{number}"
        frame, subject_quality = clean_subject(path, subject_id)
        frames.append(frame)
        quality["subjects"][subject_id] = subject_quality
        fix_path = raw_dir / f"bidmc_{number}_Fix.txt"
        subjects[subject_id] = read_subject_metadata(fix_path)
        for item in (path, fix_path):
            if item.exists():
                digest = sha256(item)
                if item.name in acquired and acquired[item.name] != digest:
                    raise NormalizationError(f"{item.name}: changed since acquisition (SHA-256 mismatch)")
                input_files.append({"file": item.name, "sha256": digest,
                                    "verified_against_acquisition": item.name in acquired})

    windows = to_windows(pd.concat(frames, ignore_index=True), window_s, min_valid_s)
    for subject_id, subject_quality in quality["subjects"].items():
        subject_windows = windows[windows["subject_id"] == subject_id]
        subject_quality["windows_generated"] = len(subject_windows)
        subject_quality["windows_with_all_variables_null"] = int(subject_windows[VARIABLES].isna().all(axis=1).sum())

    totals = {"rows_read": 0, "rows_accepted": 0, "windows_generated": len(windows)}
    rejected: dict[str, int] = {}
    nulls: dict[str, int] = dict.fromkeys(VARIABLES, 0)
    shape: dict[str, int] = dict.fromkeys(VARIABLES, 0)
    for subject_quality in quality["subjects"].values():
        totals["rows_read"] += subject_quality["rows_read"]
        totals["rows_accepted"] += subject_quality["rows_accepted"]
        for reason, count in subject_quality["rows_rejected"].items():
            rejected[reason] = rejected.get(reason, 0) + count
        for name in VARIABLES:
            nulls[name] += subject_quality["null_values_in_accepted_rows"][name]
            shape[name] += subject_quality["shape_failures_set_null"][name]
    quality["totals"] = {**totals, "rows_rejected": rejected,
                         "shape_failures_set_null": shape, "null_values_in_accepted_rows": nulls}

    manifest = {
        "source_id": SOURCE_ID,
        "source_type": SOURCE_TYPE,
        "dataset": "PhysioNet BIDMC PPG and Respiration Dataset v1.0.0",
        "doi": "10.13026/C2208R",
        "url": "https://physionet.org/content/bidmc/1.0.0/",
        "license": "Open Data Commons Attribution License v1.0 (ODC-By)",
        "attribution": "Contains data from the PhysioNet BIDMC PPG and Respiration Dataset v1.0.0 (ODC-By v1.0).",
        "citations": [
            "PhysioNet BIDMC PPG and Respiration Dataset v1.0.0. DOI 10.13026/C2208R.",
            "Pimentel MAF et al. Towards a Robust Estimation of Respiratory Rate from Pulse Oximeters. IEEE Trans Biomed Eng. 2016;64(8):1914-1923. DOI 10.1109/TBME.2016.2613124.",
            "Pollard T, Moody BE, Lehman L, Gow B, Fernandes C, Xie C, Johnson A, Mark RG, Heldt T. PhysioNet as a global platform for biomedical research. Nature Health (2026). DOI 10.1038/s44360-026-00096-z.",
        ],
        "population": "Terrestrial critically ill ICU patients; not astronauts and never loaded as astronaut data.",
        "script": "data/scripts/normalize_bidmc.py",
        "script_version": SCRIPT_VERSION,
        "parameters": {"window_s": window_s, "min_valid_s": min_valid_s, "aggregate": "median"},
        "column_mapping": {"Time [s]": "elapsed_s", **COLUMNS},
        "subjects": subjects,
        "inputs": input_files,
        "checksums_sha256": (acquisition or {}).get("checksums_sha256"),
        "timebase_policy": "Elapsed seconds from the start of each recording, aggregated into windows. No UTC timestamps or mission days are created; source dates are shifted by de-identification and are not real.",
        "measurement_context_policy": "unknown: ICU bedside monitor in a non-standardized situation, not a protocol resting measurement.",
        "missing_value_policy": "NaN and unparseable cells become null. HR, PULSE or RESP <= 0 and SpO2 outside 0-100 become null as shape failures (not clinical outliers). Rows with no values and duplicate elapsed seconds (first kept) are rejected. A window variable is null with fewer than min_valid_s valid seconds.",
        "outputs": ["numerics_1min.csv", "manifest.json", "quality_report.json"],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    windows.to_csv(out_dir / "numerics_1min.csv", index=False, lineterminator="\n")
    for name, content in (("manifest.json", manifest), ("quality_report.json", quality)):
        (out_dir / name).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"windows": windows, "manifest": manifest, "quality": quality}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--window-s", type=int, default=60)
    parser.add_argument("--min-valid-s", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        result = normalize(args.raw, args.out, args.window_s, args.min_valid_s)
    except NormalizationError as error:
        print(f"Normalization failed: {error}", file=sys.stderr)
        return 2
    totals = result["quality"]["totals"]
    print(f"Wrote {totals['windows_generated']} windows from {totals['rows_accepted']} accepted rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
