"""Parse Cursor Agent stream-json lines (ported from OpenClaw cursor-agent parser.ts)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def parse_stream_line(line: str) -> Optional[Dict[str, Any]]:
    trimmed = line.strip()
    if trimmed.startswith("\ufeff"):
        trimmed = trimmed.lstrip("\ufeff")
    if not trimmed:
        return None
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return None


def extract_session_id(ev: Dict[str, Any]) -> Optional[str]:
    """Stream-json may use ``session_id`` or ``sessionId`` depending on CLI version."""
    sid = ev.get("session_id")
    if isinstance(sid, str) and sid:
        return sid
    sid2 = ev.get("sessionId")
    if isinstance(sid2, str) and sid2:
        return sid2
    return None


def extract_tool_name(event: Dict[str, Any]) -> str:
    tc = event.get("tool_call")
    if not isinstance(tc, dict):
        return "unknown"
    for key in tc.keys():
        if str(key).endswith("ToolCall"):
            return str(key).replace("ToolCall", "")
    return str(next(iter(tc.keys()), "unknown"))


def extract_tool_args(event: Dict[str, Any]) -> str:
    tc = event.get("tool_call")
    if not isinstance(tc, dict):
        return ""
    for value in tc.values():
        if not isinstance(value, dict):
            continue
        args = value.get("args")
        if isinstance(args, dict):
            if args.get("path"):
                p = str(args["path"]).replace("\\", "/").split("/")
                return p[-1] if p else ""
            if args.get("pattern"):
                return str(args["pattern"])
            if args.get("globPattern"):
                return str(args["globPattern"])
            if args.get("command"):
                cmd = str(args["command"])
                return cmd if len(cmd) <= 40 else cmd[:40] + "..."
    return ""


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"\n... (truncated, {len(s) - max_len} chars omitted)"


def extract_tool_result(event: Dict[str, Any]) -> str:
    tc = event.get("tool_call")
    if not isinstance(tc, dict):
        return ""
    for value in tc.values():
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("result"), str):
            return _truncate(value["result"], 2000)
        if isinstance(value.get("output"), str):
            return _truncate(value["output"], 2000)
        content = value.get("content")
        if isinstance(content, list):
            texts: List[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    texts.append(str(block["text"]))
            if texts:
                return _truncate("\n".join(texts), 2000)
    return ""
