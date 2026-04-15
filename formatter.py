"""Format Cursor Agent run results for the model (ported from OpenClaw formatter.ts)."""

from __future__ import annotations

from typing import Any, Dict, List

MAX_MESSAGE_LENGTH = 3800


def format_run_result(result: Dict[str, Any]) -> List[str]:
    sections: List[str] = []
    sections.append(_build_header(result))

    file_summary = _build_file_summary(result.get("events") or [])
    if file_summary:
        sections.append(file_summary)

    conclusion = _build_conclusion(result.get("events") or [])
    if conclusion:
        sections.append(conclusion)
    elif not result.get("success") and result.get("result_text"):
        sections.append(str(result["result_text"]))

    sections.append(_build_footer(result))
    return _split_messages(sections)


def _build_header(result: Dict[str, Any]) -> str:
    ok = result.get("success")
    status = "✅" if ok else "❌"
    text = "Completed" if ok else "Failed"
    return f"{status} **Cursor Agent** {text}"


def _build_file_summary(events: List[Dict[str, Any]]) -> str:
    pairs: List[tuple] = []
    for ev in events:
        if ev.get("type") == "tool_start":
            pairs.append((ev.get("toolName") or "unknown", ev.get("toolArgs") or ""))
    if not pairs:
        return ""
    lines = ["**Tool Calls:**"]
    for name, args in pairs:
        icon = _tool_icon(str(name))
        target = f" `{args}`" if args else ""
        lines.append(f"{icon} {name}{target}")
    return "\n".join(lines)


def _tool_icon(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ("edit", "write", "replace")):
        return "📝"
    if any(x in n for x in ("read", "view")):
        return "📖"
    if any(x in n for x in ("shell", "bash", "command")):
        return "⚙️"
    if any(x in n for x in ("search", "grep", "glob", "find")):
        return "🔍"
    if any(x in n for x in ("delete", "remove")):
        return "🗑️"
    if "list" in n:
        return "📋"
    return "🔧"


def _build_conclusion(events: List[Dict[str, Any]]) -> str:
    last = ""
    for ev in events:
        if ev.get("type") == "assistant" and ev.get("text"):
            last = str(ev["text"])
    return last


def _build_footer(result: Dict[str, Any]) -> str:
    parts = [
        f"⏱ {result.get('duration_ms', 0) / 1000:.1f}s",
        f"🔧 {result.get('tool_call_count', 0)} tool calls",
    ]
    usage = result.get("usage")
    if isinstance(usage, dict):
        inp = usage.get("inputTokens")
        out = usage.get("outputTokens")
        if inp is not None and out is not None:
            parts.append(f"📊 {inp}in / {out}out tokens")
    if result.get("error"):
        parts.append(f"⚠️ {result['error']}")
    if result.get("session_id"):
        parts.append(f"💬 {result['session_id']}")
    return "\n---\n_" + " | ".join(parts) + "_"


def _split_messages(sections: List[str]) -> List[str]:
    messages: List[str] = []
    current = ""
    for section in sections:
        if len(section) > MAX_MESSAGE_LENGTH:
            if current.strip():
                messages.append(current.strip())
                current = ""
            messages.extend(_split_long_text(section, MAX_MESSAGE_LENGTH))
            continue
        candidate = current + "\n\n" + section if current else section
        if len(candidate) > MAX_MESSAGE_LENGTH:
            if current.strip():
                messages.append(current.strip())
            current = section
        else:
            current = candidate
    if current.strip():
        messages.append(current.strip())
    return messages if messages else ["Cursor Agent produced no output"]


def _split_long_text(text: str, max_len: int) -> List[str]:
    chunks: List[str] = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        candidate = current + "\n" + line if current else line
        if len(candidate) > max_len and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def extract_modified_files(events: List[Dict[str, Any]]) -> List[str]:
    files = set()
    for ev in events:
        if ev.get("type") != "tool_start":
            continue
        name = (ev.get("toolName") or "").lower()
        args = ev.get("toolArgs") or ""
        if not args:
            continue
        if any(x in name for x in ("edit", "write", "replace", "delete")):
            files.add(str(args))
    return sorted(files)
