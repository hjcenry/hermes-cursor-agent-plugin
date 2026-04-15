"""Concurrency limit and graceful process termination (ported from OpenClaw process-registry)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Optional

FORCE_KILL_DELAY_SEC = 5.0

_max_concurrent = 3
_active: Dict[str, Any] = {}
_lock = threading.Lock()


def set_max_concurrent(value: int) -> None:
    global _max_concurrent
    _max_concurrent = max(1, int(value))


def register(run_id: str, proc: Any) -> None:
    with _lock:
        _active[run_id] = proc


def unregister(run_id: str) -> None:
    with _lock:
        _active.pop(run_id, None)


def get_active_count() -> int:
    with _lock:
        return len(_active)


def is_full() -> bool:
    with _lock:
        return len(_active) >= _max_concurrent


def graceful_kill(proc: Any) -> None:
    if not proc or proc.poll() is not None:
        return
    pid = getattr(proc, "pid", None)
    if not pid:
        return
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["taskkill", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        else:
            try:
                os.killpg(os.getpgid(pid), 15)  # SIGTERM
            except (ProcessLookupError, PermissionError, AttributeError):
                proc.terminate()
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


def force_kill(proc: Any) -> None:
    if not proc or proc.poll() is not None:
        return
    pid = getattr(proc, "pid", None)
    if not pid:
        return
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        else:
            try:
                os.killpg(os.getpgid(pid), 9)
            except (ProcessLookupError, PermissionError, AttributeError):
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def kill_with_grace(proc: Any) -> None:
    graceful_kill(proc)

    def _delayed() -> None:
        time.sleep(FORCE_KILL_DELAY_SEC)
        if proc.poll() is None:
            force_kill(proc)

    t = threading.Thread(target=_delayed, daemon=True)
    t.start()


def shutdown_all() -> None:
    with _lock:
        items = list(_active.items())
        _active.clear()
    for _rid, proc in items:
        kill_with_grace(proc)


_shutdown_registered = False


def ensure_shutdown_hook() -> None:
    global _shutdown_registered
    if _shutdown_registered:
        return
    _shutdown_registered = True
    import atexit

    atexit.register(shutdown_all)
