"""Run Cursor Agent CLI and collect stream-json events (ported from OpenClaw runner.ts)."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from . import parser as stream_parser
from .process_registry import (
    ensure_shutdown_hook,
    is_full,
    kill_with_grace,
    register,
    unregister,
)
from .resolve_binary import ResolvedBinary, needs_cursor_agent_prefix

logger = logging.getLogger(__name__)


def _stderr_suggests_electron_mismatch(stderr: str) -> bool:
    s = stderr.lower()
    return "electron" in s and "known options" in s


def _windows_cmd_exe() -> str:
    """Prefer cmd.exe for ``/c`` batch invocation (ComSpec can point to non-cmd on odd setups)."""
    c = (os.environ.get("ComSpec") or "").strip()
    if c.lower().endswith("cmd.exe"):
        return c
    return os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "cmd.exe")


def build_command(
    *,
    agent_path: str,
    resolved: Optional[ResolvedBinary],
    prefix_args: Optional[List[str]],
    mode: str,
    prompt: str,
    resume_session_id: Optional[str],
    continue_session: bool,
    enable_mcp: bool,
    model: Optional[str],
) -> tuple[str, List[str], bool]:
    """Return (executable, args, needs_windows_cmd_c).

    *needs_windows_cmd_c* means the launcher is a ``.cmd``/``.bat``; on Windows we must run
    ``%ComSpec% /c <script> <args>`` with ``shell=False``. Using ``shell=True`` drops or
    mis-forwards argv so ``agent`` never reaches Cursor and Electron swallows ``-p``.
    """
    prefix_args = list(prefix_args or [])
    cli_args: List[str] = []

    if resolved:
        cli_args.append(resolved.entry_script)
    else:
        # Without `agent` subcommand, flags go to the IDE/Electron main binary — must inject.
        if not prefix_args and needs_cursor_agent_prefix(agent_path):
            prefix_args = ["agent"]

    cli_args.extend(prefix_args)
    cli_args.extend(["-p", "--trust", "--output-format", "stream-json"])

    if resume_session_id:
        cli_args.extend(["--resume", resume_session_id])
    elif continue_session:
        cli_args.append("--continue")
    elif mode != "agent":
        cli_args.extend(["--mode", mode])

    if enable_mcp:
        cli_args.extend(["--approve-mcps", "--force"])
    if model:
        cli_args.extend(["--model", model])

    cli_args.append(prompt)

    if resolved:
        return resolved.node_bin, cli_args, False

    needs_windows_cmd_c = sys.platform == "win32" and agent_path.lower().endswith((".cmd", ".bat"))
    return agent_path, cli_args, needs_windows_cmd_c


def run_cursor_agent(
    *,
    agent_path: str,
    resolved_binary: Optional[ResolvedBinary],
    project_path: str,
    prompt: str,
    mode: str,
    timeout_sec: float,
    no_output_timeout_sec: float,
    enable_mcp: bool,
    model: Optional[str] = None,
    prefix_args: Optional[List[str]] = None,
    continue_session: bool = False,
    resume_session_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous run; returns RunResult dict."""
    ensure_shutdown_hook()

    if is_full():
        return {
            "success": False,
            "result_text": (
                f"Concurrency limit reached — try again later "
                f"(active runs: see cursor_agent plugin)"
            ),
            "duration_ms": 0,
            "tool_call_count": 0,
            "error": "max concurrency reached",
            "events": [],
            "session_id": None,
            "usage": None,
        }

    rid = run_id or str(uuid.uuid4())
    start = time.time()

    cmd, args, needs_windows_cmd_c = build_command(
        agent_path=agent_path,
        resolved=resolved_binary,
        prefix_args=prefix_args,
        mode=mode,
        prompt=prompt,
        resume_session_id=resume_session_id,
        continue_session=continue_session,
        enable_mcp=enable_mcp,
        model=model,
    )

    # Windows: never use shell=True for .cmd/.bat — use ComSpec /c so "agent" stays argv[1] to Cursor.
    if sys.platform == "win32" and needs_windows_cmd_c:
        argv = [_windows_cmd_exe(), "/c", cmd, *args]
    else:
        argv = [cmd, *args]

    # Cursor stream-json is UTF-8; on Windows the default locale encoding often breaks JSON.parse.
    popen_kwargs: Dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": project_path,
        "encoding": "utf-8",
        "errors": "replace",
        "text": True,
        "bufsize": 1,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        popen_kwargs["preexec_fn"] = os.setsid  # type: ignore[assignment]

    try:
        logger.info("cursor_agent spawn argv: %s", argv)
        proc = subprocess.Popen(argv, **popen_kwargs)
    except FileNotFoundError as e:
        return {
            "success": False,
            "result_text": f"Could not start Cursor Agent: {e}",
            "duration_ms": int((time.time() - start) * 1000),
            "tool_call_count": 0,
            "error": str(e),
            "events": [],
            "session_id": None,
            "usage": None,
        }

    register(rid, proc)

    session_id: Optional[str] = None
    result_text = ""
    tool_call_count = 0
    completed = False
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []
    stderr_chunks: List[str] = []

    last_output = time.time()
    q: "queue.Queue[Optional[str]]" = queue.Queue()
    n_stream_sources = 2 if proc.stderr is not None else 1

    def _stdout_reader() -> None:
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                q.put(line)
        finally:
            q.put(None)

    def _stderr_reader() -> None:
        assert proc.stderr is not None
        try:
            for line in proc.stderr:
                stderr_chunks.append(line)
                q.put(line)
        finally:
            q.put(None)

    threading.Thread(target=_stdout_reader, daemon=True).start()
    # Some builds may write stream-json to stderr; merge both streams (count two EOF sentinels).
    if proc.stderr is not None:
        threading.Thread(target=_stderr_reader, daemon=True).start()

    deadline = start + timeout_sec

    def terminate() -> None:
        kill_with_grace(proc)

    streams_finished = 0

    try:
        while True:
            if time.time() > deadline:
                error = f"total timeout ({timeout_sec}s)"
                terminate()
                break
            if time.time() - last_output > no_output_timeout_sec and not completed:
                error = f"no output timeout ({no_output_timeout_sec}s)"
                terminate()
                break

            try:
                line = q.get(timeout=0.5)
            except queue.Empty:
                continue

            if line is None:
                streams_finished += 1
                if streams_finished >= n_stream_sources:
                    break
                continue

            last_output = time.time()
            ev = stream_parser.parse_stream_line(line)
            if not ev:
                continue

            et = ev.get("type")
            sub = ev.get("subtype")

            if et == "system" and sub == "init":
                sid = stream_parser.extract_session_id(ev)
                if sid:
                    session_id = sid

            elif et == "user":
                msg = ev.get("message") or {}
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, list) and content:
                    text = content[0].get("text") if isinstance(content[0], dict) else None
                    if text:
                        events.append({"type": "user", "text": text, "timestamp": ev.get("timestamp_ms")})

            elif et == "assistant":
                msg = ev.get("message") or {}
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, list) and content:
                    text = content[0].get("text") if isinstance(content[0], dict) else None
                    if text:
                        events.append({"type": "assistant", "text": text, "timestamp": ev.get("timestamp_ms")})

            elif et == "tool_call":
                if sub == "started":
                    tool_call_count += 1
                    events.append(
                        {
                            "type": "tool_start",
                            "toolName": stream_parser.extract_tool_name(ev),
                            "toolArgs": stream_parser.extract_tool_args(ev),
                            "timestamp": ev.get("timestamp_ms"),
                        }
                    )
                elif sub == "completed":
                    events.append(
                        {
                            "type": "tool_end",
                            "toolName": stream_parser.extract_tool_name(ev),
                            "toolResult": stream_parser.extract_tool_result(ev),
                            "timestamp": ev.get("timestamp_ms"),
                        }
                    )

            elif et == "result":
                result_text = str(ev.get("result") or "")
                usage = ev.get("usage") if isinstance(ev.get("usage"), dict) else None
                completed = True
                events.append({"type": "result", "resultData": ev, "timestamp": ev.get("timestamp_ms")})
                if ev.get("is_error") is True or sub == "error":
                    error = result_text or "Cursor Agent reported an error"
                break

        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            error = error or "process wait timed out"
            terminate()
    except Exception as e:
        error = str(e)
        logger.exception("cursor_agent runner error: %s", e)
    finally:
        unregister(rid)
        if proc.poll() is None:
            kill_with_grace(proc)

    duration_ms = int((time.time() - start) * 1000)
    stderr_text = "".join(stderr_chunks).strip()

    if not error and not completed and stderr_text:
        if _stderr_suggests_electron_mismatch(stderr_text):
            error = (
                "Cursor Agent did not return stream-json; stderr suggests the IDE binary received "
                "CLI flags instead of the agent subcommand. "
                "Set HERMES_CURSOR_AGENT_BIN to the full path of `cursor`/`agent`, or in "
                "~/.hermes/cursor_agent.json set \"prefix_args\": [\"agent\"].\n---\n"
                + stderr_text[:8000]
            )
        else:
            error = stderr_text

    if not error and not completed:
        error = "process ended without result event"

    success = bool(completed and not error)

    if not result_text and stderr_text:
        result_text = stderr_text
    if not result_text and error:
        result_text = f"Cursor Agent execution failed: {error}"

    return {
        "success": success,
        "result_text": result_text or "No analysis result obtained",
        "session_id": session_id,
        "duration_ms": duration_ms,
        "tool_call_count": tool_call_count,
        "error": error,
        "usage": usage,
        "events": events,
    }
