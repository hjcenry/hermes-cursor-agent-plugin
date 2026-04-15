"""
Hermes Cursor Agent plugin — invoke local Cursor Agent CLI (OpenClaw parity).

Install: copy this folder to ~/.hermes/plugins/cursor-agent/ or run install.sh / install.bat.
Requires: Cursor CLI: standalone ``agent`` **or** ``cursor`` (we call ``cursor agent ...``), optional ~/.hermes/cursor_agent.json.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Per-project last session id (resume), same as OpenClaw tool.ts
_last_session_by_project: Dict[str, str] = {}

DO_NOT_SUMMARIZE_DIRECTIVE = (
    "\n\n"
    + "─" * 40
    + "\n⚠️ CRITICAL — The complete Cursor Agent output is above.\n"
    "Do NOT summarize or rephrase successful runs. If the header shows **Failed** (❌), "
    "acknowledge failure briefly and cite the error — do NOT say the run succeeded.\n"
    "If **Completed** (✅), reply with a short confirmation only.\n"
    + "─" * 40
)


def _resolve_project_path(project_key: str, projects: Dict[str, str]) -> Optional[str]:
    if project_key in projects:
        return projects[project_key]
    lk = project_key.lower()
    for name, path in projects.items():
        if name.lower() == lk:
            return path
    p = Path(project_key)
    if p.exists():
        return str(p.resolve())
    return None


def _check_available(agent_path: Optional[str]) -> bool:
    if not agent_path:
        return False
    # PATH-resolved executables: isfile may be false for some Windows shims — which() paths are still valid
    p = Path(agent_path)
    if p.is_file():
        return True
    return bool(agent_path) and os.path.isfile(agent_path)


def _handle_cursor_agent(args: Dict[str, Any], **kwargs) -> str:
    from . import formatter
    from .config import load_plugin_config, coerce_prefix_args
    from .resolve_binary import (
        ResolvedBinary,
        detect_agent_path,
        needs_cursor_agent_prefix,
        resolve_agent_binary,
    )
    from .runner import run_cursor_agent
    from .process_registry import set_max_concurrent

    cfg = load_plugin_config()
    set_max_concurrent(int(cfg.get("max_concurrent", 3)))

    agent_path = (cfg.get("agent_path") or "").strip() or detect_agent_path()
    if not agent_path:
        return json.dumps(
            {
                "success": False,
                "error": "Cursor CLI not found. Install Cursor and ensure `cursor` or `agent` is on PATH, "
                "or set HERMES_CURSOR_AGENT_BIN to the full path of cursor.exe / agent in ~/.hermes/cursor_agent.json",
            },
            ensure_ascii=False,
        )

    projects: Dict[str, str] = cfg.get("projects") or {}
    project_names = list(projects.keys())

    resolved: Optional[ResolvedBinary] = None
    node_bin = (cfg.get("agent_node_bin") or "").strip()
    entry_script = (cfg.get("agent_entry_script") or "").strip()
    if node_bin and entry_script and Path(node_bin).is_file() and Path(entry_script).is_file():
        resolved = ResolvedBinary(node_bin=node_bin, entry_script=entry_script)
    else:
        resolved = resolve_agent_binary(agent_path)

    prefix = coerce_prefix_args(cfg.get("prefix_args"))
    # No standalone `agent` on PATH — use `cursor agent` (prefix matches OpenClaw intent)
    if not prefix and needs_cursor_agent_prefix(agent_path):
        prefix = ["agent"]

    project = str(args.get("project") or "").strip()
    prompt = str(args.get("prompt") or "").strip()
    mode = str(args.get("mode") or "agent").lower().strip()
    if mode not in ("agent", "ask", "plan"):
        mode = "agent"
    force_new = bool(args.get("new_session"))

    if not project or not prompt:
        return json.dumps(
            {"success": False, "error": "Missing required parameters: project and prompt"},
            ensure_ascii=False,
        )

    project_path = _resolve_project_path(project, projects)
    if not project_path:
        return json.dumps(
            {
                "success": False,
                "error": f"Project not found: {project}. "
                f"Configured projects: {', '.join(project_names) or '(none — use absolute path)'}",
            },
            ensure_ascii=False,
        )

    resume_session_id: Optional[str] = None
    if not force_new:
        resume_session_id = _last_session_by_project.get(project_path)

    result = run_cursor_agent(
        agent_path=agent_path,
        resolved_binary=resolved,
        project_path=project_path,
        prompt=prompt,
        mode=mode,
        timeout_sec=float(cfg.get("default_timeout_sec", 600)),
        no_output_timeout_sec=float(cfg.get("no_output_timeout_sec", 120)),
        enable_mcp=bool(cfg.get("enable_mcp", True)),
        model=(cfg.get("model") or None) if isinstance(cfg.get("model"), str) else None,
        prefix_args=prefix,
        resume_session_id=resume_session_id,
        continue_session=False,
    )

    # Update session for next resume (same as OpenClaw)
    sid = result.get("session_id")
    if isinstance(sid, str) and sid:
        _last_session_by_project[project_path] = sid

    messages = formatter.format_run_result(result)
    combined = "\n\n---\n\n".join(messages)
    modified = formatter.extract_modified_files(result.get("events") or [])

    text_out = combined + DO_NOT_SUMMARIZE_DIRECTIVE

    return json.dumps(
        {
            "success": bool(result.get("success")),
            "result": text_out,
            "session_id": result.get("session_id"),
            "modified_files": modified,
            "tool_call_count": result.get("tool_call_count", 0),
            "duration_ms": result.get("duration_ms", 0),
            "error": result.get("error"),
        },
        ensure_ascii=False,
    )


CURSOR_AGENT_SCHEMA = {
    "name": "cursor_agent",
    "description": (
        "Invoke the local Cursor Agent CLI to analyze, diagnose, or modify code in a project on this machine. "
        "Requires Cursor CLI and subscription. Results are returned verbatim — do not summarize.\n"
        "Configure project aliases in ~/.hermes/cursor_agent.json under \"projects\"."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "Project key from ~/.hermes/cursor_agent.json \"projects\" map, or absolute path to the repo",
            },
            "prompt": {
                "type": "string",
                "description": "Task for Cursor Agent (what to analyze, fix, or plan)",
            },
            "mode": {
                "type": "string",
                "enum": ["agent", "ask", "plan"],
                "description": "agent = full tools, may edit files under cwd (default, matches Cursor CLI); ask = read-only; plan = planning only",
            },
            "new_session": {
                "type": "boolean",
                "description": "If true, do not resume the last session for this project",
            },
        },
        "required": ["project", "prompt"],
    },
}


def register(ctx: Any) -> None:
    """Hermes plugin entry point."""

    def _check() -> bool:
        try:
            from .config import load_plugin_config
            from .resolve_binary import detect_agent_path

            cfg = load_plugin_config()
            p = (cfg.get("agent_path") or "").strip() or detect_agent_path()
            return _check_available(p)
        except Exception:
            return False

    ctx.register_tool(
        name="cursor_agent",
        toolset="cursor_agent",
        schema=CURSOR_AGENT_SCHEMA,
        handler=_handle_cursor_agent,
        check_fn=_check,
        requires_env=[],
        is_async=False,
        description=(
            "Run Cursor Agent CLI (stream-json) for deep repo work — requires `agent` binary and optional project map"
        ),
        emoji="🖱️",
    )
    logger.info("cursor_agent plugin registered")
