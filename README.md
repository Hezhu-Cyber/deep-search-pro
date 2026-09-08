<p align="center">
  <h1 align="center">🤖 Deep Search Pro</h1>
  <p align="center"><b>多智能体协作研究系统 —— 一个能讲清楚设计与取舍的 AI Agent 实战项目</b></p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.129-green" alt="FastAPI">
    <img src="https://img.shields.io/badge/LangGraph-1.0-orange" alt="LangGraph">
    <img src="https://img.shields.io/badge/deepagents-0.4.3-purple" alt="deepagents">
    <img src="https://img.shields.io/badge/WebSocket-Realtime-cyan" alt="WebSocket">
    <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT">
    <img src="https://img.shields.io/github/actions/workflow/status/Hezhu-Cyber/deep-search-pro/ci.yml" alt="CI">
  </p>
</p>

---

## 一句话简介

**Deep Search Pro** 是一个轻量、可运行的多智能体协作系统：一个「主智能体」像团队负责人一样，按任务需要动态调度「网络搜索 / 数据库查询 / RAGFlow 知识库」三类子智能体，汇总结果后直接生成 Markdown / PDF 报告；全过程通过 WebSocket 把执行轨迹实时推到前端。

项目刻意保持代码精简，但覆盖了一条完整的 **Agent 工程链路**：多智能体编排 → 工具封装 → 异步流式执行 → 实时监控 → 会话隔离 → 安全防护 → 文档产出。

---

## ✨ 核心特性

| 能力 | 说明 | 位置 |
|------|------|------|
| **多智能体编排** | 主智能体用 deepagents 调度 3 个领域子智能体，自动选择信息源并优雅降级 | `agent/` |
| **工具封装（6 个）** | 网络搜索、只读 SQL 查询、RAG 检索、文件读取、MD/PDF 生成 | `tools/` |
| **异步流式执行** | FastAPI 后台任务 + LangGraph `astream`，请求不阻塞 | `agent/main_agent.py` |
| **WebSocket 实时轨迹** | 工具调用 / 子智能体切换 / 最终结果实时推送前端 | `api/monitor.py` |
| **协程级会话隔离** | ContextVar 保证多用户并发请求数据不串扰 | `api/context.py` |
| **路径安全** | 统一路径解析，覆盖虚拟前缀、嵌套、越权等 12 类场景 | `utils/path_utils.py` |
| **只读 SQL 防护** | 表名白名单 + 语句类型校验，拒绝写操作与多语句注入 | `tools/db_tools.py` |
| **执行轨迹落盘** | 每个会话自动写入 `trace.jsonl`，可审计、可回放 | `api/monitor.py` |
| **跨平台 PDF** | WeasyPrint 优先、Word COM 兜底，摆脱 Windows 硬依赖 | `utils/word_converter.py` |
| **懒加载初始化** | LLM / Agent / RAGFlow 客户端按需创建，启动快、可测试 | `agent/llm.py` |
| **自动化测试 + CI** | 29 个单元/接口测试，GitHub Actions 自动校验 | `tests/`、`.github/` |
| **轻量评估集** | 8 条基准问题 + 关键词覆盖率脚本，支撑迭代回归 | `evals/` |
| **容器化** | Dockerfile + docker-compose 一键启动 | 根目录 |

---

## 🏗️ 架构一览

```
用户请求 (POST /api/task)
        │
        ▼
api/server.py            FastAPI 路由 / 上传 / 下载 / WebSocket
        │  asyncio.create_task（不阻塞请求线程）
        ▼
agent/main_agent.py      主智能体（deepagents 编排）异步流式执行
        │
        ├──→ 网络搜索助手     tools/tavily_tool.py        （可选）
        ├──→ 数据库查询助手   tools/db_tools.py           （可选，需 MySQL）
        ├──→ RAGFlow 知识库   tools/ragflow_tools.py      （可选，需 RAGFlow）
        └──→ 文件生成工具     generate_markdown / convert_md_to_pdf
        │
        ▼
api/monitor.py           事件上报：WebSocket 推送 + trace.jsonl 落盘
        │
        ▼
前端                      左侧实时执行轨迹 / 右侧对话 / 右侧成果文件列表
```

**数据流**：提交任务 → 主智能体规划 → 按需调用子智能体收集信息 → 汇总生成 Markdown（可转 PDF）→ 每个环节实时推送到前端并可下载成果文件。

> 未配置 MySQL / RAGFlow 也能正常运行：主智能体只会调度已配置的子智能体（优雅降级）。

---

## 🚀 快速开始

### 方式一：本地运行（推荐先跑通）

```bash
# 1. 克隆并安装（Python 3.10+）
git clone https://github.com/Hezhu-Cyber/deep-search-pro.git
cd deep-search-pro
python -m venv .venv && .venv\Scripts\activate     # Windows
# source .venv/bin/activate                        # Linux / macOS
pip install -r requirements.txt

# 2. 配置环境变量（最少 3 个即可跑通）
cp .env.example .env
#   OPENAI_BASE_URL / OPENAI_API_KEY / LLM_QWEN_MAX：任意 OpenAI 兼容服务（通义、DeepSeek、OpenAI…）
#   TAVILY_API_KEY：网络搜索（https://tavily.com 免费注册）
#   （MySQL / RAGFlow 可选，不配自动跳过）

# 3. 启动
python api/server.py        # 或 uvicorn api.server:app --reload

# 4. 打开
#    前端页面      http://localhost:8000
#    Swagger 文档  http://localhost:8000/docs
```

### 方式二：Docker 一键启动

```bash
cp .env.example .env       # 先填好 Key
docker compose up --build  # 打开 http://localhost:8000
```

### 验证安装

```bash
python -m pytest           # 运行全部测试（无需 API Key）
```

---

## 🧪 测试 / CI / 评估

```text
tests/
├── test_path_utils.py     # 路径解析 12 类场景参数化测试
├── test_context.py        # ContextVar 协程级隔离
├── test_db_guard.py       # 只读 SQL / 表名注入防护
├── test_monitor_trace.py  # 执行轨迹 JSONL 落盘
├── test_prompts.py        # 提示词配置完整性
└── test_server.py         # API 冒烟 + 上传文件名清洗 + 越权下载拦截
```

- **CI**：`.github/workflows/ci.yml` 在每次 push 时自动执行 lint + 全部测试。
- **评估**：`evals/run_eval.py` 运行 8 条基准问题并统计关键词覆盖率，报告写入 `evals/reports/`（已 gitignore），适合 prompt / 模型迭代时做量化对比：

```bash
python evals/run_eval.py --limit 3
```

---

## 📂 项目结构

```text
deep-search-pro/
├── agent/                    # 智能体层
│   ├── llm.py                # 模型懒加载（兼容 OpenAI 协议）
│   ├── prompts.py            # YAML 提示词加载
│   ├── main_agent.py         # 主智能体 + 异步流式执行引擎
│   └── subagents/            # 3 个子智能体（每个就是一段配置）
├── api/                      # Web 接口层
│   ├── server.py             # FastAPI 入口（HTTP / 上传 / 下载 / WS）
│   ├── context.py            # ContextVar 协程级会话隔离
│   └── monitor.py            # 事件上报：WebSocket + trace.jsonl
├── tools/                    # 6 个 LangChain @tool
├── utils/                    # 路径安全解析 / 跨平台 PDF 转换
├── prompt/prompts.yml        # 全部提示词（业务无关，可直接改造）
├── frontend/                 # 原生 HTML/CSS/JS 前端
├── evals/                    # 评估数据集与运行脚本
├── rawflow/                  # RAGFlow SDK 独立示例
├── tests/                    # pytest 测试
├── requirements*.txt         # 运行 / 开发 / Windows 可选依赖
├── Dockerfile / docker-compose.yml
└── .github/workflows/ci.yml
```

---

## 💡 关键设计决策（面试可直接展开）

**为什么用 deepagents 而不是手写编排逻辑？**
自己写编排要处理状态管理、tool_call 路由、流式输出、错误恢复等一堆事；deepagents 把这些封装好，我们只需定义子智能体的 name / description / tools，框架负责调度。先理解「框架能做什么」，再看源码理解「框架怎么做的」。

**为什么用 ContextVar 而不是全局变量 / threading.local？**
FastAPI 的多用户请求常跑在同一个线程的不同协程里：全局变量会被并发请求互相覆盖；`threading.local` 基于线程隔离，在 asyncio 下失效。ContextVar 是 Python 为异步设计的协程级变量，同一个请求链路内深层调用都能安全取到自己的会话上下文（见 `api/context.py` 的注释）。

**为什么 Agent / LLM / RAGFlow 客户端要懒加载？**
模块导入时不发起任何连接、不强制要求环境变量齐全，服务启动更快，也让代码库在「没有 API Key」的 CI 环境里可完整测试。

**安全上做了哪些事？**
1. 文件路径：所有工具统一走 `resolve_path`，清洗虚拟前缀、防止目录穿越与 session 嵌套；下载/列表接口只允许访问 `output/` 目录。
2. 上传：文件名清洗（只保留 basename），防止路径穿越。
3. 数据库：工具层表名白名单 + 只读语句校验，拒绝 INSERT/UPDATE/DELETE 与多语句注入；提示词层面同步约束。
4. 会话：每次任务独立工作目录 `output/session_<id>`，多用户互不可见。

**PDF 转换为什么从 Word COM 改为双引擎？**
Word COM 只能在装了 Office 的 Windows 上工作。现在默认走跨平台 WeasyPrint，Windows 有 Office 时自动回退 Word COM，从而支持 Docker / Linux 部署。

---

## 🗺️ 现状与后续方向

已完成：多智能体编排、WebSocket 实时轨迹、会话隔离、路径/只读 SQL 防护、跨平台 PDF、懒加载、测试 + CI、评估集、Docker。

可选扩展（按投入产出排序）：
1. 会话记忆持久化：把 `InMemorySaver` 换成 SqliteSaver + 前端多轮对话
2. 人工审批节点：敏感操作经 LangGraph interrupt 确认后再执行
3. 评估集扩充：按领域建 benchmark，接入自动打分
4. 结构化报告 Schema：让最终结果输出为 JSON 再渲染，提升稳定性

---

## 📄 License

[MIT](./LICENSE)
