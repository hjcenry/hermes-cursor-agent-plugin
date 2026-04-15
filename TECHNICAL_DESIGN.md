# Hermes Cursor Agent 插件 — 技术设计

> **状态**：设计稿（实现前评审）  
> **目标**：以第三方插件形式接入本机 Cursor Agent CLI，尽量不修改 Hermes 核心代码。

---

## 1. 背景与目标

### 1.1 背景

- Cursor 提供官方 **CLI（如 `agent`）**，用于在终端中对指定工作目录执行 Agent 任务（分析、只读问答、计划、改代码等），并使用 Cursor 订阅额度。
- Hermes 已有 **插件系统**（`~/.hermes/plugins/<name>/` + `plugin.yaml` + `register(ctx)`），可在不改动核心 `tools/*.py` 的前提下注册新工具。
- 参考项目 [toheart/cursor-agent](https://github.com/toheart/cursor-agent)（OpenClaw 插件）验证了「子进程调用 CLI + 解析输出」的产品形态；本设计在 **Hermes 插件语义** 下重做，**不依赖** Node/OpenClaw 运行时。

### 1.2 目标

| 编号 | 目标 |
|------|------|
| G1 | 提供工具 `cursor_agent`（名称可评审），供 Agent 在会话中调用本机 Cursor CLI。 |
| G2 | **零或极少** 修改 Hermes 仓库内核心文件；默认仅在本仓库 `plugins/cursor_agent/` 或用户目录插件中交付。 |
| G3 | 配置、安全边界、超时与并发行为清晰可文档化。 |
| G4 | Windows / Linux / macOS 行为可预期（路径、超时、终止子进程）。 |

### 1.3 非目标（首期）

- 不把 Cursor 注册为 Hermes 的 **LLM Provider**（与 chat completions 主路径无关）。
- 不实现与 OpenClaw `openclaw.plugin.json` 的兼容加载。
- 不保证与 Cursor CLI 未来大版本协议长期二进制兼容（需版本检测与文档说明）。

---

## 2. Hermes 集成点（仅使用公开扩展机制）

以下机制均为 Hermes **已有**能力，**不要求**新增核心 API（除非后续发现插件缺口）。

| 机制 | 用途 |
|------|------|
| 目录插件 | `~/.hermes/plugins/cursor-agent/` 或 `HERMES_HOME` 下 `plugins/` + 可选 `project` 插件（见 `HERMES_ENABLE_PROJECT_PLUGINS`）。 |
| `plugin.yaml` | 声明名称、版本、可选 `pip_dependencies`。 |
| `register(ctx)` | 在 `ctx.register_tool(...)` 中注册工具、schema、handler、`check_fn`。 |
| `tools.registry` | 与内置工具同一注册表；网关/CLI 通过 `toolsets` / `enabled_toolsets` 控制是否暴露。 |
| `model_tools.discover_plugins()` | 已在核心中调用；**无需**改 `model_tools.py` 若插件置于标准发现路径。 |
| `config.yaml` | 可选读取 `plugins` / 自定义节；**优先**环境变量 + 插件侧独立 JSON，避免强制改核心 schema。 |

**可选增强（仅当 MVP 发现不足时）**：

- 在 `toolsets.py` 增加一个 `cursor` 工具集别名，**或**完全由用户在配置里用 `enabled_toolsets` 列出 `cursor_agent` 等工具名（若 Hermes 支持按工具名启用）；**以现有配置能力为准**，首期可文档化「手动把 toolset 加入白名单」。

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Hermes Gateway / CLI / run_agent                           │
│  工具调度 → registry.dispatch("cursor_agent", args)        │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  插件: plugins/cursor_agent/__init__.py                      │
│  register_tool(name="cursor_agent", handler=..., check_fn=) │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  runner.py                                                   │
│  - 解析参数（project 路径、mode、prompt、timeout）            │
│  - subprocess 启动 Cursor 官方 CLI（可配置绝对路径）         │
│  - 超时 / 无输出超时 / 终止（SIGTERM → 等待 → SIGKILL）       │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  parser.py                                                   │
│  - 将 CLI stdout（如 stream-json / 文本）解析为结构化结果     │
│  - 失败时降级为原始文本片段                                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 与参考 OpenClaw 实现的对应关系

| OpenClaw 插件概念 | Hermes 插件对应 |
|-------------------|-----------------|
| `/cursor` 命令 | 由 **Agent 工具调用** `cursor_agent` 替代（网关层若需快捷指令可另做文档，不绑核心）。 |
| `runCursorAgent` | `runner.run(...)` |
| `parser.ts` | `parser.py` |
| `openclaw.json` 配置 | `plugin.yaml` + 环境变量 + 可选 `~/.hermes/cursor_agent.json` |

---

## 4. 工具契约（草案）

### 4.1 工具名

- 建议：`cursor_agent`（避免与现有内置名冲突；若与社区插件冲突，可配置前缀）。

### 4.2 参数（JSON Schema 草案）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 项目 **绝对路径**，或配置映射表中的 **别名**（见配置）。 |
| `prompt` | string | 是 | 发给 Cursor Agent 的任务描述。 |
| `mode` | string | 否 | `ask` \| `plan` \| `agent`；默认 **`agent`**（与 [Cursor CLI 概览](https://cursor.com/cn/docs/cli/overview) 一致；工作目录为工程目录）。 |
| `continue_session` | boolean | 否 | 是否延续上次会话（与 CLI `--continue` 对齐，若存在）。 |
| `resume_id` | string | 否 | 指定会话 ID（与 CLI `--resume` 对齐，若存在）。 |
| `approve_mcps` | boolean | 否 | 是否允许 MCP（与 CLI `--approve-mcps` 对齐，视官方 CLI 而定）。 |
| `timeout_sec` | integer | 否 | 覆盖默认超时。 |

### 4.3 返回值

- **成功**：字符串（Markdown 友好），包含 CLI 汇总输出；必要时附会话 ID 说明（若 CLI 在 footer 输出）。
- **失败**：使用 `tools.registry.tool_error(...)` 或项目惯例，返回 `{ "success": false, "error": "..." }`（与现有工具一致）。

### 4.4 描述（给模型看的）

- 明确说明：依赖本机 Cursor CLI、默认 `mode=agent` 可能修改工程目录内文件；`mode=ask` 为只读。

---

## 5. Cursor CLI 调用

### 5.1 可执行文件解析

优先级（建议）：

1. 环境变量 `HERMES_CURSOR_AGENT_BIN` 或 `CURSOR_AGENT_PATH`（绝对路径）。
2. `PATH` 中的 `agent`（或官方文档当前推荐的命令名）。
3. `check_fn` 失败 → 工具不可用，不在 schema 中暴露给模型（或标记为不可用）。

### 5.2 参数拼装

- **以官方 CLI 文档与本机 `agent --help` 为准**（实现阶段冻结最小参数集）。
- 工作目录：建议 `cwd=project` 的解析路径（resolved path）。
- 环境变量：透传 `CURSOR_API_KEY` / 用户已登录态（由 CLI 自身处理）。

### 5.3 输出解析

- 若官方使用 **stream-json** 行协议：逐行 JSON 解析，聚合为可读文本（对齐参考仓库逻辑）。
- 若仅为纯文本：直接返回，设置最大长度截断（与 `max_result_size_chars` 注册项对齐）。

---

## 6. 配置

### 6.1 项目别名映射

避免模型传长路径，支持：

```json
{
  "projects": {
    "my-app": "D:/work/my-app",
    "infra": "/home/user/infra"
  }
}
```

建议路径：`~/.hermes/cursor_agent.json` 或 `HERMES_HOME` 下同名文件。插件内 `load_config()` 读取。

### 6.2 默认与超时

| 项 | 默认值（建议） | 环境变量覆盖 |
|----|----------------|--------------|
| 执行超时 | 600s | `HERMES_CURSOR_AGENT_TIMEOUT_SEC` |
| 无输出超时 | 120s | `HERMES_CURSOR_AGENT_NO_OUTPUT_TIMEOUT_SEC` |
| 最大并发 | 1～3 | `HERMES_CURSOR_AGENT_MAX_CONCURRENT` |

并发可通过 **模块级 asyncio.Semaphore** 或 **asyncio.Lock** 在插件内实现，**无需**改核心。

---

## 7. 安全与合规

| 项 | 策略 |
|----|------|
| 默认模式 | `mode=agent`（与官方 CLI 默认 Agent 一致）；`cwd` 为解析后的工程目录。 |
| 写盘 / 改代码 | 默认即 `agent`；只读分析用 `mode=ask`；文档与工具描述中显著提示。 |
| 路径注入 | `project` 解析为 `Path.resolve()`，限制在允许列表（可选：仅允许 `projects` 映射内路径）。 |
| 密钥 | 不在工具参数中传 API Key；使用 CLI 与环境变量。 |
| 审计 | 日志中记录：project、mode、耗时、退出码；**不**默认记录完整 `prompt`（可配置 debug）。 |

---

## 8. 错误处理与可观测性

- 子进程非零退出：错误信息 + stderr 尾部（如最后 4KB）。
- 超时：明确提示「超时」与 `timeout_sec`。
- CLI 未安装：`check_fn` 为 false，避免模型误选。
- 日志：`logging.getLogger(__name__)`，级别 INFO/DEBUG。

---

## 9. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | `parser` 对固定 JSON 行/文本样例；`runner` 对 `echo` 模拟命令（不依赖真实 Cursor）。 |
| 集成 | 可选标记 `@pytest.mark.cursor_cli`（需本机安装 CLI）。 |
| CI | 默认跳过真实 CLI；仅跑单元与 mock。 |

---

## 10. 交付物与目录结构

```
plugins/cursor_agent/
  TECHNICAL_DESIGN.md    # 本文档
  plugin.yaml
  __init__.py            # register() 入口
  runner.py
  parser.py
  formatter.py           # 与 OpenClaw 一致的输出排版
  resolve_binary.py      # node + index.js 解析
  process_registry.py    # 并发与终止
  config.py              # ~/.hermes/cursor_agent.json
  README.md
  cursor_agent.example.json
  install.sh             # 一键安装 → ~/.hermes/plugins/cursor-agent
  install.bat
```

**安装**：在仓库中开发完成后，运行 `install.sh`（Unix）或 `install.bat`（Windows），将插件复制到 **`~/.hermes/plugins/cursor-agent`**（Windows：`%USERPROFILE%\.hermes\plugins\cursor-agent`），**无需**把插件留在 Hermes 源码树内即可使用。

**Pip 包（可选）**：后续若需 `pip install hermes-cursor-agent`，可增设 `pyproject.toml` 与 `hermes_agent.plugins` entry point；**首期目录插件即可**。

---

## 11. 演进路线

| 阶段 | 内容 |
|------|------|
| MVP | 单工具、`ask`/`agent`/`plan`、超时、项目映射、基础解析。 |
| v2 | 无输出超时、并发限制、stderr 友好展示。 |
| v3 | 与 Hermes approval 流程对接（若产品需要）、stream 长输出。 |

---

## 12. 开放问题

1. 官方 CLI 在 Windows 上的**确切**命令名与参数（实现前用 `agent --help` 冻结）。
2. Hermes 网关 `enabled_toolsets` / 按工具启用是否需文档化专用片段（仅文档，不改核心）。
3. 若与现有社区插件工具名冲突，是否采用前缀 `hermes_cursor_` 或可配置。

---

## 13. 文档修订

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-04-15 | 初稿 |
