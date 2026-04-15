# Hermes Cursor Agent Plugin

**Language:** English | [简体中文](./README.zh-CN.md)

Invoke the local **Cursor Agent CLI** (`agent` / `cursor agent`) from the **Hermes** gateway with `stream-json` output for sessions and tool calls—useful for upstream agents (e.g. Discord bots) to analyze, plan, or edit code.

**Repository**

- HTTPS: `https://github.com/hjcenry/hermes-cursor-agent-plugin.git`
- SSH: `git@github.com:hjcenry/hermes-cursor-agent-plugin.git`

---

<a id="cursor-cli-prerequisite"></a>

## Prerequisite: Install Cursor Agent (CLI)

This plugin **does not** install the Cursor CLI for you. Install **Cursor Agent** on the machine first and ensure **`agent`** works in a terminal (or only `cursor` is on PATH—the plugin can inject the `agent` subcommand).

**Official docs:** [Cursor CLI overview](https://cursor.com/cn/docs/cli/overview) (Chinese site; English docs are linked from Cursor’s main docs.)

Install per Cursor’s instructions:

**macOS / Linux / WSL:**

```bash
curl https://cursor.com/install -fsS | bash
```

**Windows (PowerShell):**

```powershell
irm 'https://cursor.com/install?win32=true' | iex
```

Verify interactively:

```bash
agent
```

For modes, non-interactive `-p`, sessions, etc., see the [official CLI overview](https://cursor.com/cn/docs/cli/overview).

---

## Features

- Tool name: `cursor_agent` (toolset `cursor_agent`)
- Non-interactive: `agent -p "…" --trust --output-format stream-json …`
- Working directory: resolved project path (`cwd`)
- Optional: per-project `session_id` resume, project aliases, timeouts, MCP toggles

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Cursor Agent CLI** | See **[Prerequisite: Install Cursor Agent](#cursor-cli-prerequisite)**. Without it, this plugin cannot run. |
| **Hermes** | Hermes plugin runtime; uses `from hermes_constants import get_hermes_home`. |
| **Account** | Cursor subscription / login via CLI (e.g. `agent login`). |

---

## Install (one command)

### Windows (PowerShell / CMD)

From this repo root (where `install.bat` lives):

```cmd
install.bat
```

### Linux / macOS

```bash
chmod +x install.sh
./install.sh
```

### What the scripts do

1. Copy plugin files to **`%USERPROFILE%\.hermes\plugins\cursor-agent`** (Windows) or **`$HOME/.hermes/plugins/cursor-agent`** (Linux/macOS). If **`HERMES_HOME`** is set, it uses that as the Hermes home.
2. If **`cursor_agent.json` does not exist**, copy **`cursor_agent.example.json`** to **`~/.hermes/cursor_agent.json`** (or **`$HERMES_HOME/cursor_agent.json`**). **Existing files are not overwritten.**
3. Remind you to **restart** the Hermes Gateway / CLI.

---

## Where to put `cursor_agent.json`

**Important:** Not inside `plugins/`—place it under the Hermes **user home** root.

| Platform | Path |
|----------|------|
| Windows | **`%USERPROFILE%\.hermes\cursor_agent.json`** |
| Linux / macOS | **`~/.hermes/cursor_agent.json`** |
| Custom | **`$HERMES_HOME/cursor_agent.json`** if you use **`HERMES_HOME`** |

Do **not** put it under `plugins/cursor-agent/`; the plugin reads `get_hermes_home() / "cursor_agent.json"`.

---

## `cursor_agent.json` fields

| Field | Type | Description |
|-------|------|-------------|
| **`projects`** | object | Alias → **absolute path** to repo. |
| **`default_timeout_sec`** | number | Total run timeout (seconds). |
| **`no_output_timeout_sec`** | number | Stall timeout (seconds). |
| **`enable_mcp`** | bool | Pass `--approve-mcps --force` (set `false` if your CLI rejects these flags). |
| **`max_concurrent`** | number | Max concurrent runs in the plugin. |
| **`model`** | string or null | `null` = CLI default; otherwise `--model`. |
| **`prefix_args`** | string array | Inserted after the executable, before standard flags; usually **`[]`**. |
| **`agent_path`** | string or null | Full path to `cursor` / `agent` / `Cursor.exe`; `null` = auto-detect. |

Environment overrides (see `config.py`), e.g. **`HERMES_CURSOR_AGENT_BIN`** → `agent_path`.

---

## Enable in Hermes

1. Add toolset **`cursor_agent`** to your Hermes gateway config (alongside `hermes-cli`, etc., per your `config.yaml`).
2. Run **install** and **restart** the Gateway.
3. Ensure **`projects`** in `cursor_agent.json` points to real paths.

---

## Troubleshooting

### 1. Electron / Chromium: `p`, `trust`, `output-format` are not known options

**Cause:** Flags reached the **Electron main process** instead of the **`agent`** subcommand.

**Fix:** Plugin tries to inject `agent` automatically. If it still fails, set **`"prefix_args": ["agent"]`** in `cursor_agent.json`, or set **`HERMES_CURSOR_AGENT_BIN`** to the full path of `cursor.exe` / `agent` (Gateway PATH may be shorter than your interactive shell).

### 2. Windows `.cmd` / argument loss

The plugin uses **`cmd.exe /c`** with **`shell=False`** for `.cmd`/`.bat`. Use the **latest** plugin code.

### 3. `session_id` is null, no stream-json

Often **encoding**: plugin forces **UTF-8** for subprocess pipes. If it still fails, confirm **`agent`** works locally; check logs for **`cursor_agent spawn argv:`** and ensure **`agent`** and **`-p`** appear.

### 4. Wrong config path

Use **`~/.hermes/cursor_agent.json`**, not under `plugins/`.

### 5. Config changes ignored

**Restart** the Gateway after edits.

### 6. Only `cursor` on PATH

If the official install provides **`agent`**, prefer that; otherwise the plugin builds `cursor` + `agent` + args.

### 7. Standalone `agent` + `prefix_args`

If your PATH already points to a **standalone `agent`**, do **not** set **`"prefix_args": ["agent"]`** (would become `agent agent …`).

### 8. Default `mode`

Default tool **`mode`** is **`agent`** (matches Cursor CLI). Use **`ask`** for read-only analysis.

---

## Repository layout

```
hermes-cursor-agent-plugin/
  README.md                 # English (default)
  README.zh-CN.md           # Chinese
  LICENSE
  plugin.yaml
  __init__.py
  config.py
  parser.py
  formatter.py
  resolve_binary.py
  process_registry.py
  runner.py
  cursor_agent.example.json
  install.bat
  install.sh
  TECHNICAL_DESIGN.md
```

---

## References

- [Cursor CLI overview](https://cursor.com/cn/docs/cli/overview)
- Plugin repo: [hermes-cursor-agent-plugin](https://github.com/hjcenry/hermes-cursor-agent-plugin)
- Install this directory to `~/.hermes/plugins/cursor-agent` for Hermes

---

## License

MIT — see [LICENSE](./LICENSE).

---

### SSH / `known_hosts` note

Adding GitHub’s **host** public key to `~/.ssh/known_hosts` only tells SSH to trust GitHub’s server fingerprint. It does **not** change, replace, or share your **private** key. The same SSH private key continues to work for **all** repositories and hosts you use it with.
