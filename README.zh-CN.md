# Hermes Cursor Agent Plugin

**语言：** [English](./README.md) | 简体中文

在 **Hermes** 网关中调用本机 **Cursor Agent CLI**（`agent` / `cursor agent`），以 `stream-json` 方式拉取会话与工具调用结果，供上层 Agent（如 Discord 机器人）做代码分析、修改与计划。

**源码仓库**

- HTTPS：`https://github.com/hjcenry/hermes-cursor-agent-plugin.git`
- SSH：`git@github.com:hjcenry/hermes-cursor-agent-plugin.git`

---

## 快速开始

1. **在本机安装 Cursor Agent（CLI）** — 见下文 [先决条件](#先决条件安装-cursor-agentcli)，终端能执行 `agent`。
2. **安装本插件**：在仓库根目录执行 Windows `install.bat` 或 Linux/macOS `./install.sh`，文件会装到 `~/.hermes/plugins/cursor-agent/`；若尚无配置，会生成 `~/.hermes/cursor_agent.json` 模板。
3. **编辑 `cursor_agent.json`** — 在 **`projects`** 里至少配置一组 **别名 → 项目绝对路径**（见 [配置 `cursor_agent.json`](#配置-cursor_agentjson)）。
4. **在 Hermes 里启用工具集** — 在 **`~/.hermes/config.yaml`** 的 **`platform_toolsets`** 里为对应平台加上 **`cursor_agent`**（见 [在 Hermes 中启用](#在-hermes-的-configyaml-中启用)），或用 **`hermes tools`** 勾选。
5. **重启** Hermes Gateway（或 CLI 会话）。
6. **冒烟测试** — 用下面 [测试用 prompt](#测试用-prompt) 发一条消息，确认会调用 `cursor_agent`。

---

<a id="cursor-cli-prerequisite"></a>

## 先决条件：安装 Cursor Agent（CLI）

本插件**不会**替你安装 Cursor CLI，需先安装 **Cursor Agent**，并确保终端能运行 **`agent`**。

**官方文档：** [Cursor CLI 概览](https://cursor.com/cn/docs/cli/overview)

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash
```

```powershell
# Windows（PowerShell）
irm 'https://cursor.com/install?win32=true' | iex
```

验证：

```bash
agent
```

---

## 安装本插件

**Windows**

```cmd
install.bat
```

**Linux / macOS**

```bash
chmod +x install.sh
./install.sh
```

脚本会把插件拷到 **`%USERPROFILE%\.hermes\plugins\cursor-agent`**（或 **`$HOME/.hermes/plugins/cursor-agent`**）。若设置了 **`HERMES_HOME`**，则使用该目录作为 Hermes 根。

若 **`cursor_agent.json` 尚不存在**，会从 **`cursor_agent.example.json`** 生成（**不会覆盖**已有文件）。

---

## 配置 `cursor_agent.json`

### 文件放在哪

| 平台 | 路径 |
|------|------|
| Windows | **`%USERPROFILE%\.hermes\cursor_agent.json`** |
| Linux / macOS | **`~/.hermes/cursor_agent.json`** |
| 自定义 | **`$HERMES_HOME/cursor_agent.json`** |

**不要**放在 `plugins/cursor-agent/` 目录里。

### `projects`：项目别名 → 绝对路径

**`projects`** 是一个对象：**键**是你在调用工具时传的 **`project` 短名**，**值**是仓库根目录的**绝对路径**（Cursor Agent 的 `cwd`）。

- **键**：任意别名，如 `my-demo`、`work`。建议不用空格。
- **值**：必须是**绝对路径**（Windows 可用 `D:/path/...` 或反斜杠转义）。

示例：

```json
{
  "projects": {
    "my-demo": "D:/project/hermes-cursor-demo",
    "work": "/home/you/code/work"
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

调用工具时 **`project`** 填 **`my-demo`** 或 **`work`**；也可以不传别名，直接传**绝对路径**字符串。

其余字段说明见下表。

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| **`projects`** | 对象 | **要用别名时必填**：别名 → **绝对路径**。 |
| **`default_timeout_sec`** | 数字 | 单次运行总超时（秒）。 |
| **`no_output_timeout_sec`** | 数字 | 无输出超时（秒）。 |
| **`enable_mcp`** | 布尔 | 是否传 `--approve-mcps --force`（CLI 不支持可改 `false`）。 |
| **`max_concurrent`** | 数字 | 插件内并发上限。 |
| **`model`** | 字符串或 null | `null` 用 CLI 默认模型；否则传 `--model`。 |
| **`prefix_args`** | 字符串数组 | 一般 **`[]`**；若仍出现 Electron 吃参数，可设 **`["agent"]`**（见 [踩坑](#踩坑与排查)）。 |
| **`agent_path`** | 字符串或 null | 显式指定 `cursor`/`agent`/`Cursor.exe` 完整路径；也可用环境变量 **`HERMES_CURSOR_AGENT_BIN`**。 |

---

## 在 Hermes 的 `config.yaml` 中启用

Hermes 按**平台**（Discord、CLI 等）加载工具。必须把工具集 **`cursor_agent`**（**下划线**，不是 `cursor-agent`）加到你使用场景对应的 **`platform_toolsets`** 列表里。

编辑 **`~/.hermes/config.yaml`**，例如：

```yaml
platform_toolsets:
  discord:
    - hermes-cli
    - cursor_agent
  cli:
    - hermes-cli
    - cursor_agent
```

把 **`discord` / `cli`** 换成你实际用的平台键；若已有列表，在列表里**追加** `- cursor_agent`，不要误删其它工具集。

**另一种方式：** 运行 **`hermes tools`**，选择平台，在清单中勾选 Cursor Agent / **`cursor_agent`**（会写回同一配置）。

修改后**重启 Gateway**。

---

## 测试用 prompt

配置好 **`projects`** 并启用工具集后，做一次联调：

**方式 A — Hermes CLI**（当前会话启用了 `cursor_agent` 时）：

```bash
hermes chat --toolsets "hermes-cli,cursor_agent" -q "请调用 cursor_agent 工具：project=my-demo，prompt=只输出项目根目录 README.md 的第一行文字。"
```

把 **`my-demo`** 换成你在 `projects` 里配置的别名。

**方式 B — Discord / 其它渠道**

用自然语言写清楚要调用的工具和参数，例如：

> 请调用 **cursor_agent**，**project** 填 `my-demo`，**prompt** 填：`只打印 README.md 第一行，不要其它内容。`

若模型没有调工具，可把指令写短，或直接在句子里写出工具名 **`cursor_agent`**。

---

## 功能概览

- 工具名：`cursor_agent`（工具集 `cursor_agent`）
- 非交互：`agent -p "…" --trust --output-format stream-json …`
- 工作目录：解析后的项目路径（`cwd`）

---

## 依赖（必读）

| 依赖 | 说明 |
|------|------|
| **Cursor Agent CLI** | 见 [先决条件](#先决条件安装-cursor-agentcli)。 |
| **Hermes** | 插件依赖 `hermes_constants`，随 Hermes 运行。 |
| **账号** | Cursor 订阅 / 登录由 CLI 处理（如 `agent login`）。 |

---

## 踩坑与排查

### 1. Electron 提示 `p`、`trust` 等不是已知选项

说明参数进了 **Electron 主进程**。可在 **`cursor_agent.json`** 设 **`"prefix_args": ["agent"]`**，或设置 **`HERMES_CURSOR_AGENT_BIN`** 为 `cursor.exe`/`agent` 的完整路径。

### 2. Windows 下 `.cmd` 丢参数

请使用**最新**插件（通过 **`cmd.exe /c`** 且 **`shell=False`** 启动批处理）。

### 3. `session_id` 为 null、无 stream-json

确认本机 **`agent`** 可用；日志里查 **`cursor_agent spawn argv:`** 是否含 **`agent`** 与 **`-p`**。

### 4. 配置文件路径错误

必须放在 **`~/.hermes/cursor_agent.json`**，不要放在 `plugins/` 下。

### 5. 工具始终不出现

确认 **`config.yaml`** 里对应平台的 **`platform_toolsets`** 已包含 **`cursor_agent`**，并已**重启 Gateway**。

### 6. 独立 `agent` 与 `prefix_args`

若 PATH 里已是**独立 `agent`**，**不要**再写 **`"prefix_args": ["agent"]`**，否则可能变成 **`agent agent …`**。

### 7. 默认模式

默认 **`mode`** 为 **`agent`**；只读分析请传 **`ask`**。

---

## 仓库结构

```
hermes-cursor-agent-plugin/
  README.md                 # English（默认）
  README.zh-CN.md           # 简体中文
  LICENSE
  plugin.yaml
  __init__.py
  …
```

---

## 参考

- [Cursor CLI 概览](https://cursor.com/cn/docs/cli/overview)
- GitHub：[hermes-cursor-agent-plugin](https://github.com/hjcenry/hermes-cursor-agent-plugin)

---

## License

MIT，见 [LICENSE](./LICENSE)。

---

### 关于 SSH 与 `known_hosts`

向 `known_hosts` 追加的是 **GitHub 服务器主机公钥**，用于校验连接对象，**不会**修改你的 **SSH 私钥**；同一把密钥仍可用于所有仓库。

---

## 联系方式

- **微信：** `hjcenry`
