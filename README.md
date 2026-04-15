# Hermes Cursor Agent Plugin

**Language:** English | [简体中文](./README.zh-CN.md)

Invoke the local **Cursor Agent CLI** (`agent` / `cursor agent`) from the **Hermes** gateway with `stream-json` output for sessions and tool calls—useful for upstream agents (e.g. Discord bots) to analyze, plan, or edit code.

**Repository**

- HTTPS: `https://github.com/hjcenry/hermes-cursor-agent-plugin.git`
- SSH: `git@github.com:hjcenry/hermes-cursor-agent-plugin.git`

---

## Quick start

1. **Install Cursor Agent (CLI)** on this machine — see [Prerequisite](#prerequisite-install-cursor-agent-cli). Confirm `agent` runs in a terminal.
2. **Install this plugin** from the repo root: Windows `install.bat`, Linux/macOS `./install.sh`. This copies files to `~/.hermes/plugins/cursor-agent/` and may create `~/.hermes/cursor_agent.json` from the example if missing.
3. **Edit `cursor_agent.json`** — add at least one **project alias → absolute path** under `projects` (see [Configuring `cursor_agent.json`](#configuring-cursor_agentjson)).
4. **Enable the toolset in Hermes** — add **`cursor_agent`** to `platform_toolsets` for your platform in **`~/.hermes/config.yaml`** (see [Enable in Hermes `config.yaml`](#enable-in-hermes-configyaml)), or use `hermes tools` to toggle it for that platform.
5. **Restart** the Hermes Gateway (or CLI session) so plugins and config reload.
6. **Smoke test** — send a message that uses the `cursor_agent` tool with your alias and a tiny prompt (see [Test prompt](#test-prompt)).

---

<a id="cursor-cli-prerequisite"></a>

## Prerequisite: Install Cursor Agent (CLI)

This plugin **does not** install the Cursor CLI. Install **Cursor Agent** first and ensure **`agent`** works in a terminal.

**Official docs:** [Cursor CLI overview](https://cursor.com/cn/docs/cli/overview)

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash
```

```powershell
# Windows (PowerShell)
irm 'https://cursor.com/install?win32=true' | iex
```

Verify:

```bash
agent
```

---

## Install this plugin (one command)

**Windows**

```cmd
install.bat
```

**Linux / macOS**

```bash
chmod +x install.sh
./install.sh
```

The script copies plugin files to **`%USERPROFILE%\.hermes\plugins\cursor-agent`** (or **`$HOME/.hermes/plugins/cursor-agent`**). If **`HERMES_HOME`** is set, that directory is used instead of `~/.hermes`.

If **`cursor_agent.json` does not exist**, it is created from **`cursor_agent.example.json`** (existing files are **not** overwritten).

---

## Configuring `cursor_agent.json`

### Where the file lives

| Platform | Path |
|----------|------|
| Windows | **`%USERPROFILE%\.hermes\cursor_agent.json`** |
| Linux / macOS | **`~/.hermes/cursor_agent.json`** |
| Custom Hermes home | **`$HERMES_HOME/cursor_agent.json`** |

Do **not** put this file inside `plugins/cursor-agent/`.

### `projects`: alias → absolute path

The **`projects`** object maps a **short name** (what you pass as the tool argument **`project`**) to the **absolute path** of a repository on disk.

- **Key** — any label you like, e.g. `my-app`, `demo`, `work`. Use ASCII; avoid spaces if unsure.
- **Value** — **absolute** path to the project root (the directory Cursor Agent should use as `cwd`).

Example:

```json
{
  "projects": {
    "my-demo": "D:/code/my-demo",
    "work": "/home/you/projects/work"
  },
  "default_timeout_sec": 600,
  "no_output_timeout_sec": 120,
  "enable_mcp": true,
  "max_concurrent": 3,
  "model": null,
  "prefix_args": [],
  "agent_path": null
}
```

When calling the tool, set **`project`** to **`my-demo`** or **`work`**, or pass an **absolute path** string directly if you did not add an alias.

Other fields (timeouts, `model`, `prefix_args`, `agent_path`) are optional; see the table below.

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| **`projects`** | object | **Required for aliases:** map **alias → absolute path**. |
| **`default_timeout_sec`** | number | Total run timeout (seconds). |
| **`no_output_timeout_sec`** | number | Stall timeout (seconds). |
| **`enable_mcp`** | bool | Pass `--approve-mcps --force` (set `false` if your CLI rejects them). |
| **`max_concurrent`** | number | Max concurrent runs in the plugin. |
| **`model`** | string or null | `null` = CLI default; otherwise `--model`. |
| **`prefix_args`** | string array | Inserted after the executable; usually **`[]`**. Use **`["agent"]`** only if Electron still receives flags (see [Troubleshooting](#troubleshooting)). |
| **`agent_path`** | string or null | Full path to `cursor` / `agent` / `Cursor.exe`; `null` = auto-detect. Can also set **`HERMES_CURSOR_AGENT_BIN`**. |

---

## Enable in Hermes `config.yaml`

Hermes loads tools per **platform** (Discord, CLI, etc.). You must include the toolset name **`cursor_agent`** (underscore, not `cursor-agent`) in the list for the platform you use.

Edit **`~/.hermes/config.yaml`** and set **`platform_toolsets`** for your platform, for example:

```yaml
platform_toolsets:
  discord:
    - hermes-cli
    - cursor_agent
  cli:
    - hermes-cli
    - cursor_agent
```

Adjust the platform key (`discord`, `cli`, `telegram`, …) to match how you run Hermes. If the list already exists, **append** `- cursor_agent` rather than replacing the whole list.

**Alternative:** run **`hermes tools`**, select your platform, and enable the **Cursor Agent** / **`cursor_agent`** toolset in the checklist (this updates the same config).

After changes, **restart the Gateway**.

---

## Test prompt

After the toolset is enabled and `projects` is set, verify end-to-end:

**Option A — Hermes CLI** (if your CLI session uses `cursor_agent`):

```bash
hermes chat --toolsets "hermes-cli,cursor_agent" -q "Use the cursor_agent tool: project=my-demo, prompt=Reply with only the first line of README.md in the repo root."
```

Replace **`my-demo`** with an alias from your `projects` map.

**Option B — Natural language (Discord / other channels)**

Send something explicit so the model picks the right tool, for example:

> Call **cursor_agent** with **project** = `my-demo` and **prompt** = `Print exactly the first line of README.md in the project root, nothing else.`

If the model does not call the tool, shorten the instruction or name the tool directly in the message.

---

## Features

- Tool name: `cursor_agent` (toolset `cursor_agent`)
- Non-interactive: `agent -p "…" --trust --output-format stream-json …`
- Working directory: resolved project path (`cwd`)

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Cursor Agent CLI** | See [Prerequisite](#prerequisite-install-cursor-agent-cli). |
| **Hermes** | Plugin runtime uses `from hermes_constants import get_hermes_home`. |
| **Account** | Cursor subscription / login via CLI (e.g. `agent login`). |

---

## Troubleshooting

### 1. Electron / Chromium: `p`, `trust`, `output-format` are not known options

Flags reached **Electron** instead of **`agent`**. Set **`"prefix_args": ["agent"]`** in `cursor_agent.json`, or **`HERMES_CURSOR_AGENT_BIN`** to the full path of `Cursor.exe` / `agent`.

### 2. Windows `.cmd` / argument loss

Use the **latest** plugin; it runs batch files via **`cmd.exe /c`** with **`shell=False`**.

### 3. `session_id` is null, no stream-json

Confirm **`agent`** works locally; check logs for **`cursor_agent spawn argv:`** (must include **`agent`** and **`-p`**).

### 4. Wrong `cursor_agent.json` path

Use **`~/.hermes/cursor_agent.json`**, not under `plugins/`.

### 5. Tool never appears

Ensure **`cursor_agent`** is in **`platform_toolsets`** for your platform and **restart** the Gateway.

### 6. Standalone `agent` + `prefix_args`

If PATH points to a **standalone `agent`**, do **not** set **`"prefix_args": ["agent"]`** (would become `agent agent …`).

### 7. Default `mode`

Default tool **`mode`** is **`agent`**. Use **`ask`** for read-only analysis.

---

## Repository layout

```
hermes-cursor-agent-plugin/
  README.md
  README.zh-CN.md
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
- [hermes-cursor-agent-plugin](https://github.com/hjcenry/hermes-cursor-agent-plugin) on GitHub

---

## License

MIT — see [LICENSE](./LICENSE).

---

### SSH / `known_hosts` note

Adding GitHub’s **host** public key to `~/.ssh/known_hosts` only verifies the server fingerprint. It does **not** change your **private** SSH key; the same key works for all repositories.
