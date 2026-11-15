"""Run an isolated real-HTTP/SQLite integration smoke from the repository root.

Uses only a temporary database and owned subprocesses. Does not exercise a browser,
claim DATA-04 delivery, or substitute for the pending analysis/alert engines.
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
    def __init__(self, env, directory):
        self.env, self.directory = env, directory
        self.process = None
        self.log = None

    def start(self):
        self.log = (self.directory / "server.log").open("a", encoding="utf-8")
        self.process = subprocess.Popen([sys.executable, "-u", "-c", SERVER], cwd=BACKEND,
                                        env=self.env, stdout=subprocess.PIPE,
                                        stderr=self.log, text=True, encoding="utf-8")
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(self.process.stdout.readline()), daemon=True).start()
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
            detail = (self.directory / "server.log").read_text(encoding="utf-8")
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
            self.process.stdout.close()
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Node 22.13+ executable (or absolute path)")
    args = parser.parse_args(argv)
    node = shutil.which(args.node)
    require(node is not None, "Node 22.13+ is required; supply --node with its executable path")
    checks = []
    with tempfile.TemporaryDirectory(prefix="astrohealth-integration-") as temporary:
        directory = Path(temporary).resolve()
        # All writable database/log paths are inside this task-owned directory.
        database = directory / "mission.db"
        require(database.parent == directory, "Database escaped the temporary workspace")
        env = {**os.environ, "ASTROHEALTH_DB_PATH": str(database),
               "ASTROHEALTH_CORS_ORIGINS": ORIGIN, "PYTHONIOENCODING": "utf-8"}
        server = Backend(env, directory)
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
            checks.append("7 unchanged frontend Fetch-client checks against actual FastAPI/SQLite")
            before, _ = request(url + "/api/astronauts/AST-001/journal?from_day=9&to_day=9")
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
            require(readings["meta"]["total"] == 1, "Reading retry did not persist exactly one record")
            checks.append("service stop/restart with persistent journal correction, stable identity and reading retry")
        finally:
            server.stop()
    print(json.dumps({"passed": True, "checks": checks, "source": "CORE-01 seven-day seed; disposable database",
                      "limitations": ["No browser/UI review", "DATA-04 pending", "Analysis and alert engines pending #14/#15"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"Integration smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)
