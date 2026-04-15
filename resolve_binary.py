"""Resolve Cursor Agent install layout to node.exe + index.js (same strategy as OpenClaw reference).

Platform notes:
- **Windows**: ``cursor.exe`` / ``cursor.cmd`` / ``cursor.bat`` are the IDE launcher; we prepend
  subcommand ``agent`` unless a standalone ``agent*.cmd`` is used.
- **macOS / Linux**: typically a ``cursor`` binary (no extension) or Linux ``*.appimage``; same
  ``agent`` prefix rule. ``node``/``index.js`` resolution uses ``node`` on Unix vs ``node.exe`` on Windows.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import FrozenSet, NamedTuple, Optional

# Basenames that are the standalone Cursor Agent CLI (do not insert ``agent`` subcommand).
_STANDALONE_AGENT_BASENAMES: FrozenSet[str] = frozenset(
    {"agent", "agent.exe", "agent.cmd", "agent.bat", "agent.sh"}
)

# Known Cursor *app* / IDE launcher basenames (insert ``agent`` when no bundled node+index.js).
_CURSOR_APP_LAUNCHER_BASENAMES: FrozenSet[str] = frozenset(
    {
        "cursor",
        "cursor.exe",
        "cursor.cmd",
        "cursor.bat",
        "cursor.sh",  # occasional wrapper on macOS/Linux
    }
)

VERSION_PATTERN = re.compile(r"^\d{4}\.\d{1,2}\.\d{1,2}-[a-f0-9]+$")


class ResolvedBinary(NamedTuple):
    node_bin: str
    entry_script: str


def _node_bin_name() -> str:
    return "node.exe" if sys.platform == "win32" else "node"


def _version_to_num(name: str) -> int:
    date_part = name.split("-", 1)[0]
    parts = date_part.split(".")
    if len(parts) != 3:
        return 0
    year, month, day = parts[0], parts[1], parts[2]
    return int(f"{year}{month.zfill(2)}{day.zfill(2)}")


def _probe_dir(directory: Path) -> Optional[ResolvedBinary]:
    node_bin = directory / _node_bin_name()
    entry = directory / "index.js"
    if node_bin.is_file() and entry.is_file():
        return ResolvedBinary(str(node_bin), str(entry))
    return None


def _probe_versions(base_dir: Path) -> Optional[ResolvedBinary]:
    versions_dir = base_dir / "versions"
    if not versions_dir.is_dir():
        return None
    try:
        entries = [p.name for p in versions_dir.iterdir() if p.is_dir()]
    except OSError:
        return None

    matched = [n for n in entries if VERSION_PATTERN.match(n)]
    matched.sort(key=_version_to_num, reverse=True)
    for ver in matched:
        result = _probe_dir(versions_dir / ver)
        if result:
            return result
    return None


def resolve_agent_binary(agent_path: str) -> Optional[ResolvedBinary]:
    """From agent.cmd / agent launcher path, find bundled node + index.js if present."""
    base = Path(agent_path).resolve().parent
    direct = _probe_dir(base)
    if direct:
        return direct
    return _probe_versions(base)


def detect_agent_path() -> Optional[str]:
    """Locate Cursor Agent entry: standalone ``agent``, else ``cursor`` (``cursor agent``).

    Order: ``agent`` on PATH → per-user install dirs (Windows ``agent.cmd``, Unix ``agent``) →
    ``cursor`` on PATH → **macOS only** ``Cursor.app/.../bin/cursor`` if PATH has no ``cursor``.
    The plugin injects subcommand ``agent`` for IDE launchers (see :func:`needs_cursor_agent_prefix`).
    """
    import shutil

    which = shutil.which("agent")
    if which:
        return which

    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or "")
    if home:
        if sys.platform == "win32":
            candidates = [
                home / "AppData" / "Local" / "cursor-agent" / "agent.cmd",
                home / ".cursor" / "bin" / "agent.cmd",
            ]
        else:
            candidates = [
                home / ".cursor" / "bin" / "agent",
                home / ".local" / "bin" / "agent",
            ]
        for p in candidates:
            if p.is_file():
                return str(p)

    # Prefer PATH so behavior matches the user's shell (then macOS bundle only as fallback).
    w = shutil.which("cursor")
    if w:
        return w

    # macOS: CLI inside the app bundle when `cursor` is not on PATH (e.g. minimal Gateway env)
    if sys.platform == "darwin" and home:
        bundle_cursor = (
            Path("/Applications/Cursor.app/Contents/Resources/app/bin/cursor"),
            home / "Applications" / "Cursor.app" / "Contents" / "Resources" / "app" / "bin" / "cursor",
        )
        for p in bundle_cursor:
            if p.is_file():
                return str(p)

    return None


def needs_cursor_agent_prefix(agent_path: str) -> bool:
    """True if *agent_path* is the Cursor IDE launcher (must run as ``<launcher> agent ...``).

    Standalone Agent CLI basenames (``agent``, ``agent.cmd``, …) return False. Works on Windows,
    macOS, and Linux; see module docstring.

    Any basename starting with ``cursor`` counts (covers ``Cursor.exe``, ``cursor.cmd``, …) except
    ``cursor-agent*`` standalone builds. Windows 8.3 short names (``CURSO~1.EXE``) are detected via
    the resolved path containing ``\\cursor\\`` or ending with ``cursor.exe``.
    """
    if not (agent_path or "").strip():
        return False
    raw = agent_path.strip()
    try:
        resolved = str(Path(raw).resolve())
    except OSError:
        resolved = raw
    name = Path(raw).name.lower()

    if name in _STANDALONE_AGENT_BASENAMES:
        return False
    # Standalone "cursor-agent" distribution — already a full CLI, no extra "agent" subcommand.
    if name.startswith("cursor-agent"):
        return False

    if name in _CURSOR_APP_LAUNCHER_BASENAMES:
        return True
    # Any cursor*.exe / cursor* shim (covers edge renames we do not list explicitly).
    if name.startswith("cursor") and not name.startswith("cursor-agent"):
        return True
    # Linux AppImage: cursor-x.y.AppImage
    if name.endswith(".appimage") and name.startswith("cursor"):
        return True

    # Windows: 8.3 short path like C:\PROGRA~1\...\CURSO~1.EXE — basename no longer "cursor.exe".
    rl = resolved.lower().replace("/", "\\")
    if sys.platform == "win32" and "cursor-agent" not in rl:
        if rl.endswith("\\cursor.exe") or rl.endswith("cursor.exe"):
            return True
        # Typical install: ...\Local\Programs\cursor\Cursor.exe or ...\cursor\...
        if "\\cursor\\" in rl and name.endswith(".exe"):
            return True

    return False


def is_cursor_cli_executable(agent_path: str) -> bool:
    """Deprecated alias — use :func:`needs_cursor_agent_prefix`."""
    return needs_cursor_agent_prefix(agent_path)
