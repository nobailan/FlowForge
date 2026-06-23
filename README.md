# FlowForge — Agent 协作架构实验平台

> 可视化搭建多 Agent 协作模式，量化评估每种架构的优劣。
> 以 [OpenCode](https://github.com/opencode-ai/opencode) 为 Agent 执行内核，每个节点具备完整的代码读写、Shell 执行、搜索等能力。

## 项目背景

现有 AI Agent 框架普遍关注"单个 Agent 能做什么"，但缺少一个核心问题的答案：

**"多个 Agent 怎么协作最好？"**

LangGraph Studio 提供了画布，但没有评估能力。RAGAS 等评测框架提供了指标，但没有结构对比。开发者选架构只能靠直觉。

FlowForge 填补这个空白——让"架构设计"变成可实验、可量化、可对比的工程问题。

## 核心特性

- **可视化画布** — 拖拽 6 种节点（LLM、Tool、Retriever、Subagent、Condition、Loop），自由连线构建协作拓扑
- **5 种内置模板** — Supervisor-Worker、Sequential Chain、Parallel Experts、Conditional Branch、Reflection Loop，一键加载
- **OpenCode 执行内核** — 每个 LLM/Tool/Retriever/Subagent 节点背后是一个完整的 Agent Session，具备 Bash、文件读写、代码搜索、Web 搜索等全套工具
- **实时监控控制台** — 终端风格的 ExecutionConsole，展示每个节点的思考过程、工具调用、Token 消耗
- **评测引擎** — 加载测试集，自动计算成功率、延迟、Token 成本、工具调用效率；支持多架构并排对比
- **暗色主题** — 全界面 VS Code Tokyo Night 风格

## 快速启动

### 环境要求

- Python 3.11+
- Node.js 18+ & Bun 1.3+
- PostgreSQL 16

### 一键启动

```powershell
.\start.ps1
```

依次启动三个服务（各开独立窗口）：
- **OpenCode Server**（4096）— Agent 执行引擎
- **FlowForge Backend**（8000）— FastAPI + LangGraph
- **FlowForge Frontend**（5173）— React + ReactFlow

浏览器打开 `http://localhost:5173`

### 关闭

```powershell
.\stop.ps1        # 停止全部服务 + 清理卡住的执行
.\stop.ps1 -a     # 额外清掉所有 Python/Node/Bun 进程
```

## 使用流程

1. 打开 `http://localhost:5173`
2. 左侧面板加载一个模板（📋 Templates），或手动拖拽节点到画布连线
3. 点击节点 → 右侧面板配置 System Prompt、模型、超时等参数
4. 点击顶部 **▶ Run** → 输入任务问题 → 观察右侧 ExecutionConsole 实时日志
5. 执行完成后，展开节点卡片查看 Agent 思考链和工具调用详情
6. 底部 **📋 Output Terminal** 展示各节点最终输出
7. 保存架构后可评测、对比不同架构的指标

## 节点类型

| 节点 | 能力 | OpenCode Agent |
|------|------|---------------|
| 🤖 LLM | 通用 Agent，全工具集 | build |
| 🔧 Tool | 受限执行（bash + read） | build |
| 📚 Retriever | 代码检索（glob + grep + read） | explore |
| 👥 Subagent | 嵌套子 Agent，独立上下文 | general |
| 🔀 Condition | 条件路由，基于上游输出分支 | — |
| 🔄 Loop | 循环控制，continue/exit | — |

## 架构设计

```
浏览器 (React + ReactFlow)
    │
    ▼
FlowForge 后端 (FastAPI + LangGraph)
    │  HTTP API
    ▼
OpenCode Server (Bun / TypeScript)
    │  Anthropic SDK
    ▼
DeepSeek API
```

### 技术栈

| 层 | 技术选型 |
|----|---------|
| 前端 | React 18, TypeScript, React Flow, Zustand, Tailwind CSS |
| 后端 | Python 3.11, FastAPI, LangGraph, SQLAlchemy, PostgreSQL |
| Agent 引擎 | OpenCode (Bun, TypeScript, Effect) |
| LLM | DeepSeek V4 Pro (Anthropic 兼容接口) |
| 实时通信 | WebSocket + SSE 桥接 |

### 关键设计决策

1. **动态 AgentState** — 使用 `node_outputs` 嵌套 dict 存储任意拓扑的节点输出，TypedDict 无法约束动态 key
2. **Annotated + Reducer** — 所有 state 字段添加 Annotated reducer，支持 LangGraph 并行 fan-out
3. **execute_sync()** — 每个节点在独立线程中运行 `asyncio.run()`，彻底隔离 event loop，解决多节点死锁
4. **线程化 SSE 监听** — MonitorBridge 在 daemon 线程中连接 OpenCode SSE，避免与主流程 async 死锁
5. **JSONB 存储** — 画布全量存为单列 JSONB，MVP 不拆表
6. **Agent 边界管控** — 每个节点配备严格的 System Prompt 限定职责范围，防止 Agent 越界

## Prompt 编写原则

多 Agent 协作中最关键的教训：每个节点都是完整 Agent，没有边界约束就会越界。

**应该做的**：
- 明确输出范围：`"Output ONLY the result number. No analysis."`
- 引用上游输出：`"Supervisor 指令：{{supervisor.output}}"`
- 限制工具使用：`"Do NOT use any tools. Just evaluate the text."`

**不应该做的**：
- 模糊指令：`"分析项目"`（Agent 会探索整个代码库）
- 忘记下游节点的 `{{node_id.output}}` 引用
- 复杂任务设太短的 timeout（每个节点至少 30-60 秒）

## 目录结构

```
harness_lab/
├── frontend/src/
│   ├── components/    # Canvas, ConfigPanel, ExecutionConsole, OutputTerminal
│   ├── store/         # Zustand (canvasStore + appStore)
│   ├── api/           # 后端 API 客户端
│   └── types/         # TypeScript 类型
├── backend/src/
│   ├── engine/        # GraphBuilder, Executor, Monitor, Templates
│   ├── nodes/         # 6 种节点实现
│   ├── adapter/       # OpenCode HTTP 客户端 + SSE 桥接 + 工作空间管理
│   ├── api/           # REST + WebSocket 路由
│   └── evaluator/     # 评测引擎
├── evaluation/        # 黄金测试集
├── start.ps1          # 一键启动
├── stop.ps1           # 停止 + 清理
└── README.md
```

## 常见问题排查

| 现象 | 检查 |
|------|------|
| 所有节点 "Waiting..." 不动 | 后端是否在运行：`curl localhost:8000/api/health` |
| 节点打叉，output 为空 | 展开节点卡片看错误信息。常见原因：超时/prompt 模糊/API 400 |
| Token 异常高 | 某个 Agent 在过度探索。System Prompt 加 `"Do NOT use any tools"` |
| 前端 ECONNREFUSED | 后端没启动（8000 端口） |
| WebSocket 连接失败 | 控制台有轮询兜底，等几秒即可 |

## License

MIT
