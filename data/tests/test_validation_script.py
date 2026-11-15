"""DATA-06 check: the mission validation script passes against the real backend."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_mission_rules_passes(tmp_path: Path) -> None:
    out = tmp_path / "validation_result.json"
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_mission_rules.py"), "--out", str(out)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert len(result["checks"]) == 10 and all(item["passed"] for item in result["checks"])
