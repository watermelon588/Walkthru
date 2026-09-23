"""DEV ONLY: build the extension and run the whole stack with one command. Remove before production.

    .\\dev            (Windows, from the repo root; dev.cmd calls this file)
    apps/api/.venv/Scripts/python dev.py

Starts API :8000, web :5173, easy fixture :8101 and hard fixture :8102, builds the extension into
apps/extension/.output/chrome-mv3, prints the URLs, and stops everything on Ctrl+C.
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, "apps", "api", ".venv", "Scripts" if os.name == "nt" else "bin", "python")
NODE = "node"
EXT = os.path.join(ROOT, "apps", "extension")

SERVERS = {
    # name: (command, cwd, port, url to check)
    # No --reload: uvicorn's Windows reload uses console Ctrl+C events and hangs under a supervisor.
    # This script restarts the API itself when apps/api/app changes (see api_changed).
    "api": ([PY, "-m", "uvicorn", "app.main:app", "--port", "8000", "--timeout-graceful-shutdown", "3"], os.path.join(ROOT, "apps", "api"), 8000, "http://127.0.0.1:8000/health"),
    "web": ([NODE, "node_modules/vite/bin/vite.js", "--port", "5173", "--strictPort"], os.path.join(ROOT, "apps", "web"), 5173, "http://localhost:5173/"),
    "fixtures": ([PY, "evals/serve.py"], ROOT, 8101, "http://127.0.0.1:8102/"),
}
COLORS = {"api": "36", "web": "35", "fixtures": "33", "ext": "32", "dev": "1"}
procs: list[subprocess.Popen] = []
API_SRC = os.path.join(ROOT, "apps", "api", "app")


def api_mtime() -> float:
    newest = 0.0
    for folder, _, files in os.walk(API_SRC):
        for f in files:
            if f.endswith(".py"):
                newest = max(newest, os.path.getmtime(os.path.join(folder, f)))
    return newest


def say(name: str, line: str) -> None:
    print(f"\033[{COLORS[name]}m[{name:<8}]\033[0m {line}", flush=True)


def pipe(name: str, proc: subprocess.Popen) -> None:
    for raw in proc.stdout:  # type: ignore[union-attr]
        line = raw.decode("utf-8", "replace").rstrip()
        if line:
            say(name, line)


def start(name: str, cmd: list[str], cwd: str) -> subprocess.Popen:
    # Windows: each server gets its own hidden console. uvicorn --reload stops its worker with a console
    # Ctrl+C event, and in a shared console that event would also kill this script and the whole stack.
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    env = os.environ | {"PYTHONUNBUFFERED": "1", "FORCE_COLOR": "1"}
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, creationflags=flags)
    procs.append(proc)
    threading.Thread(target=pipe, args=(name, proc), daemon=True).start()
    return proc


def port_busy(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status < 500
    except Exception:  # noqa: BLE001 - not up yet
        return False


def kill(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        if os.name == "nt":  # kill the whole tree: vite and uvicorn spawn children
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
        else:
            proc.terminate()
        proc.wait(timeout=10)


def stop_all() -> None:
    for proc in procs:
        kill(proc)


def main() -> int:
    busy = [f"{n} :{p}" for n, (_, _, p, _) in SERVERS.items() if port_busy(p)] + (["fixtures :8102"] if port_busy(8102) else [])
    if busy:
        say("dev", f"Already in use: {', '.join(busy)}. Stop those servers first (or close the other terminal).")
        return 1

    say("ext", "building extension ...")
    ext = start("ext", [NODE, "node_modules/wxt/bin/wxt.mjs", "build"], EXT)
    running = {name: start(name, cmd, cwd) for name, (cmd, cwd, _, _) in SERVERS.items()}

    ext_ok = ext.wait() == 0
    deadline = time.time() + 90
    pending = {n: u for n, (_, _, _, u) in SERVERS.items()}
    while pending and time.time() < deadline:
        pending = {n: u for n, u in pending.items() if not up(u)}
        if any(p.poll() is not None for p in running.values()):
            say("dev", "a server exited during startup; see its output above")
            stop_all()
            return 1
        time.sleep(1)

    out = os.path.join(EXT, ".output", "chrome-mv3")
    print(
        "\n\033[1mWalkthru dev stack\033[0m  (Ctrl+C stops everything)\n"
        "  Web app        http://localhost:5173        dashboard: /app\n"
        "  API            http://127.0.0.1:8000/docs\n"
        "  Easy fixture   http://127.0.0.1:8101\n"
        "  Hard fixture   http://127.0.0.1:8102\n"
        f"  Extension      {'built' if ext_ok else 'BUILD FAILED, see [ext] lines'}: {out}\n"
        "                 chrome://extensions > Reload on Walkthru (first time: Load unpacked from the folder above)\n"
        + (f"  Still starting: {', '.join(pending)}\n" if pending else ""),
        flush=True,
    )
    seen = api_mtime()
    try:
        while all(p.poll() is None for p in running.values()):
            time.sleep(1)
            now = api_mtime()
            if now != seen:  # API source changed: restart it cleanly
                seen = now
                say("api", "source changed, restarting API ...")
                old = running["api"]
                kill(old)
                procs.remove(old)
                cmd, cwd, _, _ = SERVERS["api"]
                running["api"] = start("api", cmd, cwd)
        say("dev", "a server stopped; shutting down the rest")
    except KeyboardInterrupt:
        say("dev", "stopping ...")
    finally:
        stop_all()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # child output has spinners and arrows; never crash a reader
    signal.signal(signal.SIGINT, signal.default_int_handler)
    sys.exit(main())
