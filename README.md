# Hermes Cursor Agent Plugin

在 **Hermes** 网关中调用本机 **Cursor Agent CLI**（`agent` / `cursor agent`），以 `stream-json` 方式拉取会话与工具调用结果，供上层 Agent（如 Discord 机器人）做代码分析、修改与计划。

**源码仓库**

- HTTPS：`https://github.com/hjcenry/hermes-cursor-agent-plugin.git`
- SSH：`git@github.com:hjcenry/hermes-cursor-agent-plugin.git`

---

<a id="cursor-cli-prerequisite"></a>

## 先决条件：安装 Cursor Agent（CLI）

本插件**不会**替你安装 Cursor CLI，你需要先在机器上安装 **Cursor Agent**，并确保终端能运行 **`agent`**（或仅有 `cursor` 时由插件补全子命令）。

**官方文档（必读）：** [Cursor CLI 概览](https://cursor.com/cn/docs/cli/overview)

按官方说明，安装方式如下（与文档一致）：

**macOS / Linux / WSL：**

```bash
curl https://cursor.com/install -fsS | bash
```

**Windows（PowerShell）：**

```powershell
irm 'https://cursor.com/install?win32=true' | iex
```

安装完成后，在终端执行一次交互式会话，确认可用：

```bash
agent
```

更多用法（模式、非交互 `-p`、会话续写等）见 [官方 CLI 概览](https://cursor.com/cn/docs/cli/overview)。

---

## 功能概览

- 工具名：`cursor_agent`（工具集 `cursor_agent`）
- 非交互：`agent -p "…" --trust --output-format stream-json …`
- 工作目录：解析后的项目路径（`cwd`），限制在配置的工程目录下操作
- 可选：按项目恢复会话 `session_id`、项目别名映射、超时与 MCP 开关

---

## 依赖（必读）

| 依赖 | 说明 |
|------|------|
| **Cursor Agent CLI** | 见上文 **[先决条件：安装 Cursor Agent](#cursor-cli-prerequisite)**；未完成安装则本插件无法工作。 |
| **Hermes** | 本仓库是 **Hermes 插件**，需由 Hermes 加载；插件内 `from hermes_constants import get_hermes_home`，与 Hermes 主工程一起运行。 |
| **账号** | Cursor 订阅 / 登录状态由 CLI 自行处理（如 `agent login`）。 |

---

## 一键安装

### Windows（PowerShell / CMD）

在**本仓库根目录**（含 `install.bat`）执行：

```cmd
install.bat
```

### Linux / macOS

```bash
chmod +x install.sh
./install.sh
```

### 安装脚本做了什么

1. 将插件文件复制到  
   **`%USERPROFILE%\.hermes\plugins\cursor-agent`**（Windows）  
   或 **`$HOME/.hermes/plugins/cursor-agent`**（Linux/macOS）。  
   环境变量 **`HERMES_HOME`** 若已设置，则根目录为 **`$HERMES_HOME`**（与 Hermes 一致）。
2. 若 **`cursor_agent.json` 尚不存在**，则把 **`cursor_agent.example.json`** 复制为：  
   **`%USERPROFILE%\.hermes\cursor_agent.json`**（或 **`$HERMES_HOME/cursor_agent.json`**）。  
   **不会覆盖**已有配置文件。
3. 提示你 **重启 Hermes Gateway / CLI** 以加载插件。

---

## 配置文件：`cursor_agent.json` 放在哪里？

**重要：与插件目录分开，放在 Hermes 用户目录根下。**

| 平台 | 路径 |
|------|------|
| Windows | **`%USERPROFILE%\.hermes\cursor_agent.json`** |
| Linux / macOS | **`~/.hermes/cursor_agent.json`** |
| 自定义 | 若 Hermes 使用 **`HERMES_HOME`**，则为 **`$HERMES_HOME/cursor_agent.json`** |

**不要**放在 `plugins/cursor-agent/` 里；插件代码通过 `get_hermes_home() / "cursor_agent.json"` 读取。

安装脚本会在首次安装时自动生成一份模板；若你手动创建，可复制本仓库的 **`cursor_agent.example.json`** 再改。

---

## `cursor_agent.json` 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| **`projects`** | 对象 | 项目别名 → **绝对路径**。模型传短别名即可，避免传长路径。 |
| **`default_timeout_sec`** | 数字 | 单次运行总超时（秒）。 |
| **`no_output_timeout_sec`** | 数字 | 无输出超时（秒）。 |
| **`enable_mcp`** | 布尔 | 是否传 `--approve-mcps --force`（若 CLI 不支持可改为 `false`）。 |
| **`max_concurrent`** | 数字 | 插件内并发上限。 |
| **`model`** | 字符串或 null | `null` 表示使用 CLI 默认模型；否则传 `--model`。 |
| **`prefix_args`** | 字符串数组 | 插入在可执行文件之后、标准参数之前；一般 **`[]`** 即可。 |
| **`agent_path`** | 字符串或 null | 显式指定 `cursor`/`agent`/`Cursor.exe` 的完整路径；`null` 用自动探测。 |

环境变量可覆盖部分项（见 `config.py`），例如：

- **`HERMES_CURSOR_AGENT_BIN`** → `agent_path`
- **`HERMES_CURSOR_AGENT_TIMEOUT_SEC`** 等

---

## 在 Hermes 中启用

1. 在 Hermes 网关配置里启用工具集 **`cursor_agent`**（与 `hermes-cli` 等并列，视你的 `config.yaml` 而定）。
2. **安装** 并 **重启** Gateway。
3. 确认 `cursor_agent.json` 里 **`projects`** 已配置好路径。

---

## 踩坑与排查（常见问题）

### 1. Electron / Chromium 提示：`p`、`trust`、`output-format` 不是已知选项

**含义：** 参数被传给了 **Cursor 主进程（Electron）**，而不是 `agent` 子命令。

**处理：**

- 插件已尽量自动插入 `agent` 子命令；若仍失败，在 **`cursor_agent.json`** 中设置：  
  **`"prefix_args": ["agent"]`**  
- 或设置环境变量 **`HERMES_CURSOR_AGENT_BIN`** 为 **`cursor.exe` / `agent` 的完整路径**（与 `where cursor` 在交互终端里一致；Gateway 服务的 PATH 可能更短）。

### 2. Windows 下 `.cmd` 启动与参数丢失

插件对 **`.cmd`/`.bat`** 使用 **`cmd.exe /c`** 且 **`shell=False`**，避免参数被吞掉。请使用**最新**插件代码。

### 3. `session_id` 为 null、没有任何 stream-json

**可能原因：** 子进程 stdout 在 Windows 上按 **系统代码页** 解码，**UTF-8** 的 JSON 行解析失败。插件已强制 **`encoding=utf-8`**。

**若仍失败：** 确认本机已安装并可运行 **`agent`**（见官方文档）；查看 Hermes 日志中的 **`cursor_agent spawn argv:`** 是否包含 **`agent`** 与 **`-p`**。

### 4. `cursor_agent.json` 放错位置

放在 **`~/.hermes/cursor_agent.json`**，而不是 `plugins/*/cursor_agent.json`。放错位置会导致仍用默认空配置。

### 5. 修改配置后不生效

修改 JSON 后一般 **重启 Gateway** 再试。

### 6. 仅 `cursor` 无独立 `agent`

多数环境安装官方 CLI 后 **`agent`** 可用；若 PATH 只有 **`cursor`**，插件会拼 **`cursor` + `agent` + 参数**。

### 7. `prefix_args` 与独立 `agent` 可执行文件

若 PATH 里直接是 **独立 `agent`**（不是 `cursor`），**不要**再写 **`"prefix_args": ["agent"]`**，否则可能变成 **`agent agent …`**。

### 8. 默认模式

默认 **`mode`** 为 **`agent`**（与官方 CLI 一致）；只读分析请显式传 **`ask`**。

---

## 仓库结构（开源发布）

```
hermes-cursor-agent-plugin/
  README.md                 # 本说明
  LICENSE                   # MIT
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
  TECHNICAL_DESIGN.md       # 可选设计说明
```

---

## 参考

- [Cursor CLI 概览](https://cursor.com/cn/docs/cli/overview)
- 本插件源码：[hermes-cursor-agent-plugin](https://github.com/hjcenry/hermes-cursor-agent-plugin)
- Hermes 侧需将本目录作为插件安装到 `~/.hermes/plugins/cursor-agent`

---

## License

MIT，见 [LICENSE](./LICENSE)。
