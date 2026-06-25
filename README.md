# FlowForge — Agent 协作架构实验平台

> 可视化搭建多 Agent 协作模式，量化评估每种架构的优劣。
> 以 [OpenCode](https://github.com/opencode-ai/opencode) 为 Agent 执行内核，每个节点具备完整的代码读写、Shell 执行、搜索等能力。

## 版本演进

| 版本 | 主题 | 核心变化 |
|------|------|---------|
| v0.1 | MVP | ReactFlow 画布 + LangGraph 引擎 + 6 种节点 + 5 个模板 |
| v0.2 | Agent 化 | 接入 OpenCode，每个节点变成完整 Agent Session |
| v0.3 | 可视化 | 暗色主题 + 执行控制台 + 实时监控 |
| v0.4 | 自动化 | 拓扑分析引擎 + Auto Prompt 生成 + Apply & Run |
| v0.5 | Token 优化 | 工件存储 + JSON 约束 + 工具按需加载 + 滑动窗口 |
| **v0.6** | **实时监控** | **队列桥接跨 event loop 推送，thinking/工具调用实时可见** |

## 核心特性

- **可视化画布** — 拖拽 6 种节点（LLM、Tool、Retriever、Subagent、Condition、Loop），自由连线构建协作拓扑
- **5 种内置模板** — Supervisor-Worker、Sequential Chain、Parallel Experts、Conditional Branch、Reflection Loop，一键加载
- **OpenCode 执行内核** — 每个节点背后是一个完整的 Agent Session，具备 Bash、文件读写、搜索等工具
- **Token 优化引擎 (v0.5)** — 工件存储（Redis）、JSON 强制输出、工具按需分配、滑动窗口，综合节省 38-80% Token
- **自动 Prompt 生成 (v0.4)** — 拓扑分析 + 角色分类 + Prompt 自动生成 + 一键应用并运行
- **实时流式监控 (v0.6)** — 队列桥接跨 event loop 推送，Agent 思考过程、工具调用实时滚动显示，Token 精确统计不虚高
- **评测引擎** — 加载测试集，自动计算成功率、延迟、Token 成本、工具调用效率；支持多架构并排对比
- **暗色主题** — 全界面 VS Code Tokyo Night 风格

## 快速启动

### 环境要求

- Python 3.11+
- Node.js 18+ & Bun 1.3+
- PostgreSQL 16
- Redis 5.0+ (已内置在 E:\redis\，start.ps1 自动启动)

### 一键启动

```powershell
.\start.ps1
```

依次启动四个服务（各开独立窗口）：
- **Redis**（6379）— 工件存储
- **OpenCode Server**（4096）— Agent 执行引擎
- **FlowForge Backend**（8000）— FastAPI + LangGraph
- **FlowForge Frontend**（5173）— React + ReactFlow

浏览器打开 `http://localhost:5173`

### 关闭

```powershell
.\stop.ps1        # 停止全部服务 + 清理卡住的执行（含 Redis）
.\stop.ps1 --all  # 额外清掉所有 Python/Node/Bun 进程
```

## 使用流程

1. 打开 `http://localhost:5173`
2. 左侧面板加载一个模板（📋 模板），或手动拖拽节点到画布连线
3. 点击节点 → 右侧面板配置 System Prompt、模型、超时等参数
4. 点击 ✨ **自动 Prompt** → 输入任务描述 → 自动分析拓扑并生成优化 Prompt → 应用并运行
5. 或直接点击顶部 **▶ 运行** → 输入任务问题 → 观察右侧控制台实时日志
6. 执行完成后，展开节点卡片查看 Agent 思考链和工具调用详情
7. 底部 **📋 输出终端** 展示各节点最终输出
8. 保存架构后可评测、对比不同架构的指标

## 架构设计

```
浏览器 (React + ReactFlow)
    │
    ▼
FlowForge 后端 (FastAPI + LangGraph)
    │  HTTP API          │ Redis
    ▼                    ▼
OpenCode Server      Artifact Store
(Bun / TypeScript)   (工件存储)
    │
    ▼
DeepSeek API
```

### 技术栈

| 层 | 技术选型 |
|----|---------|
| 前端 | React 18, TypeScript, React Flow, Zustand, Tailwind CSS |
| 后端 | Python 3.11, FastAPI, LangGraph, SQLAlchemy, PostgreSQL |
| 缓存 | Redis 5.0 (工件存储 + 会话缓存) |
| Agent 引擎 | OpenCode (Bun, TypeScript, Effect) |
| LLM | DeepSeek V4 Pro (Anthropic 兼容接口) |
| 实时通信 | WebSocket + SSE 桥接 |

### v0.5 Token 优化详解

#### 🗄️ 工件存储 (Artifact Store)
Agent 之间不再传递文件内容，只传引用。基于 Redis，Key 格式 `artifact:{exec_id}:{node}:{file}:v{version}`。
```
v0.4: Worker A → "config.py 内容：[5000行全文]" → Worker B 上下文塞满
v0.5: Worker A → "[REF: artifact://config.py#v1]" → Worker B 按需取用
```
效果：文件传递 **15,000T → 500T（-97%）**

#### 📜 JSON 强制输出
每个节点 System Prompt 末尾注入 JSON Schema，禁止啰嗦输出。
- Dispatcher → `{"plan": [...]}`
- Worker → `{"status", "result", "refs"}`
- Aggregator → `{"answer", "confidence"}`
效果：单节点输出 **800T → 200T（-75%）**

#### 🛠️ 工具按需分配
根据节点角色 + 任务关键词自动分配工具白名单。
- Dispatcher / Aggregator：0 工具
- Reader Worker：glob, grep, read
- Code Worker：read, write, bash, grep
效果：工具定义 overhead **800T → 150-450T（-69%）**

#### 🔄 滑动窗口
裁剪对话历史，只保留任务目标 + 最近 K 轮，模块已实现待集成。
效果：长对话节省 **40-60%**

## 节点类型

| 节点 | 能力 | v0.5 工具策略 |
|------|------|--------------|
| 🤖 LLM Agent | 通用 Agent | 按角色自动分配（0-4 个工具） |
| 🔧 Tool | 受限执行 | 按任务关键词分配（bash/read） |
| 📚 Retriever | 代码检索 | glob + grep + read |
| 👥 Subagent | 嵌套子 Agent | 按需分配 |
| 🔀 Condition | 条件路由 | 零工具 |
| 🔄 Loop | 循环控制 | 零工具 |

## Prompt 编写原则

多 Agent 协作中最关键的教训：每个节点都是完整 Agent，没有边界约束就会越界。

**v0.5 强制 JSON 输出格式**：
```json
// Worker 节点
{"status": "ok", "result": "<concise, max 200 chars>"}

// Dispatcher 节点
{"plan": [{"worker_id": "...", "task": "specific task"}]}

// Aggregator 节点
{"answer": "<final>", "sources": [...], "confidence": 0.95}
```

**应该做的**：
- 用英文写 System Prompt（比中文更省 Token，约束力更强）
- 明确输出范围：`"Output ONLY the result. No analysis."`
- 使用工件引用：`"[REF: artifact://key]"` 代替复制文件内容
- 在 Auto Prompt 中描述任务 → 自动生成适配拓扑的优化 Prompt

**不应该做的**：
- 模糊指令：`"分析项目"`（Agent 会探索整个代码库，烧 Token）
- 忘记限制工具：一个只读节点不应该挂 bash/write 权限
- 把用户原问题直接发给 no-op 路由节点（用固定指令代替）

## 目录结构

```
harness_lab/
├── frontend/src/
│   ├── components/    # Canvas, ConfigPanel, ExecutionConsole, OutputTerminal, AutoPrompt
│   ├── store/         # Zustand (canvasStore + appStore)
│   ├── api/           # 后端 API 客户端
│   └── types/         # TypeScript 类型
├── backend/src/
│   ├── engine/        # GraphBuilder, Executor, Topology, PromptGenerator, ArtifactStore, SlidingWindow
│   ├── nodes/         # 6 种节点实现 (llm, tool, retriever, subagent, condition, loop)
│   ├── adapter/       # OpenCode HTTP 客户端 + SSE 桥接 + 工作空间管理
│   ├── api/           # REST + WebSocket 路由
│   └── evaluator/     # 评测引擎
├── document/          # 需求文档 + 版本说明
├── E:\redis\          # Redis 5.0 (Windows)
├── start.ps1          # 一键启动（Redis + OpenCode + Backend + Frontend）
├── stop.ps1           # 停止 + 清理
└── README.md
```

## 常见问题排查

| 现象 | 检查 |
|------|------|
| 所有节点 "等待中..." 不动 | `curl localhost:8000/api/health` |
| 节点打叉，latency 正好 60s | 超时。检查 allowed_tools 是否给够，或增大 timeout |
| Token 异常高 / 执行完成后还在涨 | 重启前端，v0.6 已修复此 Bug |
| 控制台无实时输出 | 确认后端重启后重新加载模板（旧模板缓存无 execution_id） |
| 前端白屏 | 刷新页面；ErrorBoundary 会自动兜底 |
| WebSocket 连接失败 | 控制台有 3 秒轮询兜底 |
| Redis 连接失败 | ArtifactStore 自动回退内存存储，不影响执行 |
| fan_out 节点超时 | 重新从侧边栏加载模板，确保使用最新版本 |

## License

MIT
