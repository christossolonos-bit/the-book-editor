"""Start/stop the book editor Vite server with Cursor sessions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PID_FILE = ROOT / ".cursor" / "editor-server.pid"
PORT = 5173


def read_stdin() -> dict:
    try:
        raw = sys.stdin.read().strip()
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def emit(payload: dict | None = None) -> None:
    sys.stdout.write(json.dumps(payload or {}) + "\n")


def pids_on_port(port: int) -> list[int]:
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    pids: list[int] = []
    for part in out.replace(",", " ").split():
        if part.isdigit():
            pid = int(part)
            if pid and pid not in pids:
                pids.append(pid)
    return pids


def vite_pids() -> list[int]:
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                r"Get-CimInstance Win32_Process -Filter \"Name = 'node.exe'\" | "
                r"Where-Object { $_.CommandLine -match 'vite' -and $_.CommandLine -match 'final book editor' } | "
                r"Select-Object -ExpandProperty ProcessId",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    return [int(p) for p in out.split() if p.isdigit()]


def stop() -> None:
    pids = set(pids_on_port(PORT)) | set(vite_pids())
    if PID_FILE.exists():
        try:
            pids.add(int(PID_FILE.read_text(encoding="utf8").strip()))
        except Exception:
            pass
        try:
            PID_FILE.unlink()
        except Exception:
            pass

    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass


def start() -> None:
    if pids_on_port(PORT):
        return

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    log_path = ROOT / ".cursor" / "editor-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a", encoding="utf8")

    # On Windows, npm is typically npm.cmd and needs a shell.
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
        shell=(sys.platform == "win32"),
    )
    PID_FILE.write_text(str(proc.pid), encoding="utf8")


def main() -> None:
    _ = read_stdin()
    action = sys.argv[1] if len(sys.argv) > 1 else "stop"
    if action == "start":
        start()
    else:
        stop()
    emit({})


if __name__ == "__main__":
    main()
