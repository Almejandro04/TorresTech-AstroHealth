"""Download a small subset of PhysioNet BIDMC v1.0.0 and verify its checksums.

Run from the repository root:
    .\\.venv\\Scripts\\python.exe data\\scripts\\acquire_bidmc.py [--subjects 01 02 03]

Writes to data/raw/bidmc/ (git-ignored): the selected bidmc_##_Numerics.csv and
bidmc_##_Fix.txt files, SHA256SUMS.txt, and acquisition.json. Every file is
checked against the official SHA256SUMS.txt; any mismatch fails the run.

Source: PhysioNet BIDMC PPG and Respiration Dataset v1.0.0, DOI 10.13026/C2208R,
Open Data Commons Attribution License v1.0 (ODC-By).
"""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://physionet.org/files/bidmc/1.0.0/"
FILES_DIR = "bidmc_csv/"
CHECKSUMS = "SHA256SUMS.txt"
DEFAULT_SUBJECTS = ("01", "02", "03")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "raw" / "bidmc"
USER_AGENT = "astrohealth-data-acquisition/1.0"
TIMEOUT_S = 60


class AcquisitionError(RuntimeError):
    """A download or checksum failure; nothing is reported as verified."""


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AcquisitionError(f"Could not download {url}: {error}") from error


def parse_checksums(text: str) -> dict[str, str]:
    """Map each listed path to its SHA-256 (lines are `<hash>  <path>`)."""
    sums = {}
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def expected_hash(sums: dict[str, str], name: str) -> tuple[str, str]:
    """Find a file in SHA256SUMS by suffix, preferring the bidmc_csv/ copy."""
    matches = [path for path in sums if path == name or path.endswith("/" + name)]
    preferred = [path for path in matches if path.endswith(FILES_DIR + name)]
    chosen = preferred or matches
    if len(chosen) != 1:
        raise AcquisitionError(f"{name}: expected one entry in {CHECKSUMS}, found {len(chosen)}")
    return chosen[0], sums[chosen[0]]


def acquire(subjects: list[str], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    checksum_bytes = fetch(BASE_URL + CHECKSUMS)
    (out_dir / CHECKSUMS).write_bytes(checksum_bytes)
    sums = parse_checksums(checksum_bytes.decode("utf-8"))

    files = []
    for subject in subjects:
        for suffix in ("_Numerics.csv", "_Fix.txt"):
            name = f"bidmc_{subject}{suffix}"
            listed_path, expected = expected_hash(sums, name)
            url = BASE_URL + FILES_DIR + name
            content = fetch(url)
            actual = hashlib.sha256(content).hexdigest()
            if actual != expected:
                raise AcquisitionError(f"{name}: SHA-256 {actual} does not match {expected}")
            (out_dir / name).write_bytes(content)
            files.append({
                "file": name,
                "url": url,
                "checksum_entry": listed_path,
                "sha256": actual,
                "bytes": len(content),
                "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

    record = {
        "source_id": "PHYSIONET-BIDMC-1.0.0",
        "doi": "10.13026/C2208R",
        "license": "Open Data Commons Attribution License v1.0 (ODC-By)",
        "checksums_url": BASE_URL + CHECKSUMS,
        "checksums_sha256": hashlib.sha256(checksum_bytes).hexdigest(),
        "subjects": [f"bidmc_{s}" for s in subjects],
        "files": files,
    }
    (out_dir / "acquisition.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subjects", nargs="+", default=list(DEFAULT_SUBJECTS),
                        help="two-digit subject numbers (default: 01 02 03)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if any(len(s) != 2 or not s.isdigit() or not 1 <= int(s) <= 53 for s in args.subjects):
        parser.error("subjects are two-digit numbers from 01 to 53")
    try:
        record = acquire(args.subjects, args.out)
    except AcquisitionError as error:
        print(f"Acquisition failed (network or checksum): {error}", file=sys.stderr)
        return 2
    print(f"Verified {len(record['files'])} files in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
