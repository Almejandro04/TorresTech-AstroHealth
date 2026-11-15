"""Run an isolated real-HTTP/SQLite integration smoke from the repository root.

Uses only temporary databases and owned subprocesses. Stages: the CORE-01 seed
(replay, CORS, frontend client, restart) and the DATA-04 30-day mission (baseline,
generated alert, resolution, nulls, frontend guards). Does not exercise a browser.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SEED = ROOT / "docs" / "examples" / "mission_seed.json"
MISSION = ROOT / "data" / "synthetic" / "mission_ast101_ast102.json"
ORIGIN = "http://127.0.0.1:5175"
SERVER = """
import json, socket, uvicorn
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
sock.listen(128)
print(json.dumps({'port': sock.getsockname()[1]}), flush=True)
uvicorn.Server(uvicorn.Config('app.main:app', log_level='warning')).run(sockets=[sock])
"""


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(argv, env):
    result = subprocess.run(argv, cwd=BACKEND, env=env, capture_output=True,
                            text=True, encoding="utf-8", timeout=60)
    if result.returncode:
        raise RuntimeError(f"Command failed: {argv!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def request(url, *, headers=None, method="GET"):
    with urlopen(Request(url, headers=headers or {}, method=method), timeout=5) as response:
        body = response.read()
        payload = json.loads(body) if body and "application/json" in response.headers.get("Content-Type", "") else None
        return payload, response.headers


class Backend:
    def __init__(self, env):
        self.env = env
        self.process = None
        self.log = []
        self.readers = []

    def start(self):
        self.log = []
        self.process = subprocess.Popen([sys.executable, "-u", "-c", SERVER], cwd=BACKEND,
                                        env=self.env, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8")
        lines = queue.Queue()
        process = self.process
        def read_errors():
            for line in process.stderr:
                self.log.append(line)
                if len(self.log) > 200:
                    del self.log[0]
        self.readers = [
            threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True),
            threading.Thread(target=read_errors, daemon=True),
        ]
        for reader in self.readers:
            reader.start()
        try:
            first = lines.get(timeout=15)
            self.url = "http://127.0.0.1:" + str(json.loads(first)["port"])
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    health, _ = request(self.url + "/api/health")
                    if health["data"]["status"] == "ok":
                        return self.url
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.05)
            raise RuntimeError("FastAPI did not become healthy")
        except Exception:
            self.stop()
            detail = "".join(self.log)
            raise RuntimeError("Backend startup failed: " + detail) from None

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for reader in self.readers:
                reader.join(timeout=1)
            self.process.stdout.close()
            self.process.stderr.close()
            self.process = None
            self.readers = []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Node 22.13+ executable (or absolute path)")
    args = parser.parse_args(argv)
    node = shutil.which(args.node)
    require(node is not None, "Node 22.13+ is required; supply --node with its executable path")
    checks = []
    with tempfile.TemporaryDirectory(prefix="astrohealth-integration-") as temporary:
        directory = Path(temporary).resolve()
        # The writable database stays inside this task-owned directory.
        # Server diagnostics use drained pipes, avoiding Windows log-file locks.
        database = directory / "mission.db"
        require(database.parent == directory, "Database escaped the temporary workspace")
        env = {**os.environ, "ASTROHEALTH_DB_PATH": str(database),
               "ASTROHEALTH_CORS_ORIGINS": ORIGIN, "PYTHONIOENCODING": "utf-8"}
        server = Backend(env)
        def import_day(day):
            output = command([sys.executable, "-m", "app.database", "import-json",
                              str(SEED), "--until-day", str(day)], env)
            try:
                return json.loads(output)
            except ValueError as error:
                raise RuntimeError(f"Import did not return JSON: {output!r}") from error
        try:
            imported = import_day(3)
            require(imported["committed"], "Initial import was not committed")
            url = server.start()
            summary, _ = request(url + "/api/astronauts/AST-001/summary")
            require(summary["data"]["mission_day"] == 3, "First import exposed a future day")
            history, _ = request(url + "/api/astronauts/AST-001/readings")
            ids3 = [r["reading_id"] for r in history["data"]]
            require(history["meta"]["total"] == 3, "Day-3 history count differs")
            import_day(5)
            repeat = import_day(5)
            history, _ = request(url + "/api/astronauts/AST-001/readings")
            require(history["meta"]["total"] == 5 and ids3 == [r["reading_id"] for r in history["data"][:3]],
                    "Replay changed previous IDs or duplicated records")
            require(repeat["records"]["readings"]["created"] == 0, "Repeated import created readings")
            checks.append("real HTTP day-3 -> day-5 replay and idempotence")
            replay = import_day(3)
            cutoff = replay["post_import"]["cutoffs"]["AST-001"]
            require(cutoff == "2026-11-03T12:00:00Z", "Historical handoff leaked a future cutoff")
            historical, _ = request(url + "/api/astronauts/AST-001/summary?as_of=" + cutoff)
            latest, _ = request(url + "/api/astronauts/AST-001/summary")
            require(historical["data"]["mission_day"] == 3 and latest["data"]["mission_day"] == 5,
                    "Historical replay changed current storage or leaked future observations")
            checks.append("historical replay cutoff while preserving later stored observations")
            _, headers = request(url + "/api/astronauts", method="OPTIONS", headers={
                "Origin": ORIGIN, "Access-Control-Request-Method": "GET"})
            require(headers.get("Access-Control-Allow-Origin") == ORIGIN, "Explicit CORS origin was not allowed")
            checks.append("actual CORS preflight for the documented review origin")
            import_day(7)
            output = command([node, str(BACKEND / "scripts" / "check_frontend_api.mjs"), url], env)
            print(output, end="")
            checks.append("8 frontend Fetch/history checks against actual FastAPI/SQLite")
            before, _ = request(url + "/api/astronauts/AST-001/journal?from_day=9&to_day=9")
            readings_before, _ = request(url + "/api/astronauts/AST-001/readings?from_day=10&to_day=10")
            old_url = url
            server.stop()
            try:
                request(old_url + "/api/health")
            except (URLError, TimeoutError, ConnectionError):
                pass
            else:
                raise RuntimeError("Owned backend still responds after shutdown")
            url = server.start()
            after, _ = request(url + "/api/astronauts/AST-001/journal?from_day=9&to_day=9")
            require(after["data"] == before["data"] and after["meta"]["total"] == 1,
                    "Journal data/identity changed or duplicated across restart")
            require(after["data"][0]["sleep_hours_last_night"] == 0 and after["data"][0]["notes"] == "Corrected",
                    "Journal correction or zero sleep was not persisted")
            readings, _ = request(url + "/api/astronauts/AST-001/readings?from_day=10&to_day=10")
            require(readings["meta"]["total"] == 2 and readings["data"] == readings_before["data"],
                    "Reading retry/later observation changed identity or count across restart")
            checks.append("service stop/restart with persistent journal correction, stable identity and reading retry")
        finally:
            server.stop()
    mission = mission_stage(node, checks)
    print(json.dumps({"passed": True, "checks": checks,
                      "source": "CORE-01 seven-day seed and DATA-04 30-day synthetic mission; disposable databases",
                      "mission_stage": mission,
                      "limitations": ["No automated browser/UI review",
                                      "Baseline and alert rules are experimental and not clinically validated"]},
                     indent=2))
    return 0


def end_of_day(day):
    return f"2026-11-{day:02d}T23:59:59Z"


def mission_stage(node, checks):
    """DATA-04 mission -> experimental baseline -> generated alert, over real HTTP."""
    results = {}
    with tempfile.TemporaryDirectory(prefix="astrohealth-mission-") as temporary:
        directory = Path(temporary).resolve()
        database = directory / "mission30.db"
        require(database.parent == directory, "Database escaped the temporary workspace")
        env = {**os.environ, "ASTROHEALTH_DB_PATH": str(database),
               "ASTROHEALTH_CORS_ORIGINS": ORIGIN, "PYTHONIOENCODING": "utf-8"}
        server = Backend(env)

        def import_mission():
            return json.loads(command([sys.executable, "-m", "app.database", "import-json",
                                       str(MISSION), "--until-day", "30"], env))

        try:
            first = import_mission()
            require(first["committed"] and first["records"]["readings"]["created"] == 63
                    and first["records"]["journal"]["created"] == 32, "Mission import counts differ")
            repeat = import_mission()
            require(all(counts["created"] == 0 and counts["updated"] == 0
                        for counts in repeat["records"].values()), "Repeated mission import changed rows")
            results["import"] = {"created": {k: v["created"] for k, v in first["records"].items()},
                                 "repeat": {k: v["repeated"] for k, v in repeat["records"].items()}}
            checks.append("DATA-04 30-day mission import and idempotent re-import (all repeated)")

            url = server.start()
            base = url + "/api/astronauts/AST-101"

            def summary(day):
                return request(f"{base}/summary?as_of={end_of_day(day)}")[0]["data"]

            def alerts(day):
                return request(f"{base}/alerts?as_of={end_of_day(day)}&limit=1000")[0]

            day5 = summary(5)
            require(day5["baselines"]["heart_rate_bpm"]["status"] == "insufficient_data"
                    and day5["alert_summary"]["evaluation_status"] == "insufficient_data"
                    and alerts(5)["meta"]["evaluation_status"] == "insufficient_data",
                    "Day 5 must have no reference and no evaluation")
            results["day_5"] = {"baseline": "insufficient_data", "evaluation_status": "insufficient_data"}

            baseline = summary(9)["baselines"]["heart_rate_bpm"]
            day9 = alerts(9)
            require(baseline["status"] == "available" and abs(baseline["value"] - 72.2) < 1e-9,
                    "Day 9 baseline must be available at 72.2")
            require(day9["meta"]["evaluation_status"] == "available"
                    and not [a for a in day9["data"] if a["status"] == "active"],
                    "Isolated day-9 spike must not alert")
            results["day_9"] = {"baseline": baseline["value"], "evaluation_status": "available", "active_alerts": 0}

            day19 = [a for a in alerts(19)["data"] if a["status"] == "active"]
            require(len(day19) == 1, f"Day 19 must have exactly one active alert, got {len(day19)}")
            alert = day19[0]
            require(alert["rule_id"] == "DEMO-HR-CHANGE" and alert["severity"] == "warning"
                    and alert["window_start"] == "2026-11-18T12:00:00Z"
                    and alert["window_end"] == "2026-11-19T12:00:00Z"
                    and alert["observed_value"] == 80 and alert["explanation"].strip(),
                    f"Day 19 alert differs: {alert}")
            results["day_19"] = {key: alert[key] for key in ("alert_id", "rule_id", "severity", "window_start",
                                                             "window_end", "observed_value", "baseline_value")}

            day22 = alerts(22)["data"]
            require(len(day22) == 1 and day22[0]["alert_id"] == alert["alert_id"]
                    and day22[0]["status"] == "resolved" and day22[0]["resolved_at"] == "2026-11-22T12:00:00Z",
                    f"Day 22 must resolve the same alert: {day22}")
            results["day_22"] = {"alert_id": day22[0]["alert_id"], "status": "resolved",
                                 "resolved_at": day22[0]["resolved_at"]}

            views30 = [alerts(30) for _ in range(3)]
            require(all(v["meta"]["total"] == 1 and [a["alert_id"] for a in v["data"]] == [alert["alert_id"]]
                        for v in views30), "Day 30 must keep one alert without duplicates")
            results["day_30"] = {"totals": [v["meta"]["total"] for v in views30], "alert_id": alert["alert_id"]}
            checks.append("real HTTP AST-101 cutoffs: day 5 no reference, day 9 isolated spike, "
                          "day 19 warning, day 22 resolved, day 30 single alert")

            short_summary = request(url + "/api/astronauts/AST-102/summary")[0]["data"]["alert_summary"]
            short_alerts = request(url + "/api/astronauts/AST-102/alerts")[0]
            require(short_summary["evaluation_status"] == "insufficient_data"
                    and short_alerts["meta"]["evaluation_status"] == "insufficient_data"
                    and short_alerts["data"] == [], "AST-102 must stay insufficient_data")
            results["AST-102"] = "insufficient_data"
            checks.append("AST-102 short history is insufficient_data, never an empty available list")

            readings = request(f"{base}/readings?from_day=11&to_day=13&limit=1000")[0]["data"]
            rest = {r["mission_day"]: r for r in readings if r["measurement_context"] == "rest"}
            journal = request(f"{base}/journal?from_day=13&to_day=15")[0]["data"]
            require(rest[12]["heart_rate_bpm"] is None and rest[12]["spo2_percent"] is not None
                    and rest[13]["respiratory_rate_bpm"] is None, "Scenario nulls did not reach the API as null")
            require([j["mission_day"] for j in journal] == [13, 15], "Day-14 journal must be absent")
            # Contract 3.5: the card shows the latest NON-NULL value at the cutoff in any
            # context, with that observation's own time and context. Day 12 is an even day,
            # so its 17:00 exercise reading is later than the null rest reading at 12:00.
            history = request(f"{base}/readings?as_of={end_of_day(12)}&limit=1000")[0]["data"]
            expected = max((r for r in history if r["heart_rate_bpm"] is not None),
                           key=lambda r: (r["timestamp"], r["reading_id"]))
            heart = summary(12)["latest_metrics"]["heart_rate_bpm"]
            require(heart["value"] is not None and heart["record_id"] == expected["reading_id"]
                    and heart["record_id"] != rest[12]["reading_id"]
                    and heart["timestamp"] == expected["timestamp"]
                    and heart["measurement_context"] == expected["measurement_context"],
                    f"Day-12 card must show the latest non-null heart rate with its own time: {heart}")
            results["nulls"] = {"day_12_rest_heart_rate_bpm": None, "day_13_rest_respiratory_rate_bpm": None,
                                "day_14_journal": "absent",
                                "day_12_heart_rate_card": {key: heart[key] for key in
                                                           ("value", "timestamp", "mission_day",
                                                            "measurement_context", "record_id")}}
            checks.append("scenario nulls/absence preserved; day-12 heart-rate card shows the latest non-null "
                          "observation with its own timestamp and context, not the null rest reading")

            if node is None:
                results["frontend_guards"] = "skipped (Node 22.13+ not available)"
            else:
                output = command([node, str(BACKEND / "scripts" / "check_mission_views.mjs"), url, "AST-101",
                                  end_of_day(19), end_of_day(22)], env)
                print(output, end="")
                results["frontend_guards"] = output.strip()
                checks.append("frontend responses.* and matchesView guards on AST-101 days 19 and 22")
        finally:
            server.stop()
    return results


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"Integration smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)
