"""Load cursor_agent plugin configuration from ~/.hermes/cursor_agent.json and env."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_constants import get_hermes_home


def _config_path() -> Path:
    return get_hermes_home() / "cursor_agent.json"


def load_plugin_config() -> Dict[str, Any]:
    """Merge defaults, JSON file, and environment overrides."""
    cfg: Dict[str, Any] = {
        "projects": {},
        "default_timeout_sec": 600,
        "no_output_timeout_sec": 120,
        "enable_mcp": True,
        "max_concurrent": 3,
        "model": None,
        "prefix_args": [],
        "agent_path": None,
        "agent_node_bin": None,
        "agent_entry_script": None,
    }

    path = _config_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if v is not None:
                        cfg[k] = v
        except (OSError, json.JSONDecodeError):
            pass

    # Environment overrides
    if os.getenv("HERMES_CURSOR_AGENT_BIN"):
        cfg["agent_path"] = os.getenv("HERMES_CURSOR_AGENT_BIN", "").strip()
    if os.getenv("HERMES_CURSOR_AGENT_NODE_BIN"):
        cfg["agent_node_bin"] = os.getenv("HERMES_CURSOR_AGENT_NODE_BIN", "").strip()
    if os.getenv("HERMES_CURSOR_AGENT_ENTRY_SCRIPT"):
        cfg["agent_entry_script"] = os.getenv("HERMES_CURSOR_AGENT_ENTRY_SCRIPT", "").strip()
    if os.getenv("HERMES_CURSOR_AGENT_TIMEOUT_SEC"):
        try:
            cfg["default_timeout_sec"] = int(os.getenv("HERMES_CURSOR_AGENT_TIMEOUT_SEC", ""))
        except ValueError:
            pass
    if os.getenv("HERMES_CURSOR_AGENT_NO_OUTPUT_TIMEOUT_SEC"):
        try:
            cfg["no_output_timeout_sec"] = int(os.getenv("HERMES_CURSOR_AGENT_NO_OUTPUT_TIMEOUT_SEC", ""))
        except ValueError:
            pass
    if os.getenv("HERMES_CURSOR_AGENT_MAX_CONCURRENT"):
        try:
            cfg["max_concurrent"] = int(os.getenv("HERMES_CURSOR_AGENT_MAX_CONCURRENT", ""))
        except ValueError:
            pass
    mc = os.getenv("HERMES_CURSOR_AGENT_ENABLE_MCP", "").lower()
    if mc in ("true", "1", "yes", "false", "0", "no"):
        cfg["enable_mcp"] = mc in ("true", "1", "yes")

    # Normalize keys from JSON that might use camelCase (OpenClaw-style)
    if "defaultTimeoutSec" in cfg and "default_timeout_sec" not in cfg:
        cfg["default_timeout_sec"] = cfg.get("defaultTimeoutSec", cfg["default_timeout_sec"])
    if "noOutputTimeoutSec" in cfg:
        cfg["no_output_timeout_sec"] = cfg.get("noOutputTimeoutSec", cfg["no_output_timeout_sec"])
    if "enableMcp" in cfg:
        cfg["enable_mcp"] = bool(cfg.get("enableMcp", cfg["enable_mcp"]))
    if "maxConcurrent" in cfg:
        cfg["max_concurrent"] = int(cfg.get("maxConcurrent", cfg["max_concurrent"]))
    if "prefixArgs" in cfg and isinstance(cfg["prefixArgs"], list):
        cfg["prefix_args"] = [str(x) for x in cfg["prefixArgs"]]

    projects = cfg.get("projects") or {}
    if isinstance(projects, dict):
        cfg["projects"] = {str(k): str(v) for k, v in projects.items()}
    else:
        cfg["projects"] = {}

    return cfg


def coerce_prefix_args(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        import shlex

        return shlex.split(value, posix=os.name != "nt")
    return []
