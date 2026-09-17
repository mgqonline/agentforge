# ⚡ AgentForge · 智炼工坊
### 新一代全栈 AI 架构师实操练兵场 (Agent-Native Engineering & Sandbox Platform)

> **Python 3.10+ · LangChain · LangGraph · OpenAI SDK · MCP · ChromaDB · Monaco Sandbox**  
> 从 Prompt 提示词工程到生产级 Multi-Agent 架构的完整工程化实操路径

---

## 📋 目录

- [项目简介](#-项目简介)
- [快速开始](#-快速开始)
- [技术栈总览](#-技术栈总览)
- [模块目录](#-模块目录)
  - [01 Prompt 工程](#01-prompt-engineering--prompt-工程)
  - [02 Function Calling](#02-function-calling--工具调用)
  - [03 MCP 协议](#03-mcp--model-context-protocol)
  - [04 RAG 检索增强生成](#04-rag--检索增强生成)
  - [05 Embedding 向量化](#05-embedding--向量化)
  - [06 Agent 基础](#06-agent-basics--agent-基础-langgraph)
  - [07 Agent 深度记忆](#07-advanced-memory--agent-深度记忆)
  - [08 多模态 RAG](#08-multimodal--多模态-rag)
  - [09 评估与可观测性](#09-evaluation--评估与可观测性)
  - [10 生产级实战](#10-production--生产级实战)
  - [11 Python 高性能进阶](#11-python-advanced--python-高性能进阶)
  - [12 FastAPI 模型网关与 SSE](#12-fastapi-advanced--大模型高性能-api-网关与-sse-流式输出)
  - [13 SQLAlchemy 状态持久化](#13-sqlalchemy-advanced--智能体状态持久化与用户记忆资产)
  - [14 Celery 长任务与分布式编排](#14-celery-advanced--大模型长耗时任务解耦与多-agent-分布式编排)
  - [15 企业级全栈 Agent 架构协同](#15-agent-architecture--企业级全栈-agent-架构协同实战)
  - [16 人脸识别](#16-face-recognition--人脸识别)
  - [17 Transformers 原理](#17-transformers-basics--transformer-原理与优化)
  - [18 推理部署](#18-inference-serving--高性能推理与部署架构)
  - [19 模型微调](#19-model-finetuning--大模型微调实战)
  - [20 高阶 RAG](#20-graph-rag--知识引擎与高阶-rag)
  - [21 复杂智能体](#21-multi-agent-scale--复杂多智能体协同)
  - [22 AI 安全](#22-ai-security--ai-安全与红蓝对抗)
  - [23 端侧计算](#23-edge-ai--端侧与异构计算)
- [实战项目](#-实战项目)
  - [RepoSense 代码助手](#1-reposense--代码仓库智能助手)
  - [hybrid_rag 混合检索系统](#2-hybrid_rag--企业级混合检索系统)
  - [document_processor 文档解析器](#3-document_processor--多格式文档解析器)
  - [autogen_coder 代码 Agent](#4-autogen_coder--自动化代码-agent)
- [文档索引](#-文档索引)

---

## 🎯 项目简介

本项目是一个系统性的 **AI 工程化学习仓库**，以「实践驱动、文档先行、模块化」为核心准则，覆盖当前 AI 工程全栈技术链路：

```
Prompt 设计 → 工具调用 → MCP 协议 → RAG 检索 → Embedding
     ↓
LangGraph Agent → 深度记忆 → 多 Agent 协作 → HITL 人机协同
     ↓
多模态理解 → Transformer 原理 → LoRA 微调 → 推理优化
     ↓
Ragas 评估 → LangSmith 追踪 → 生产部署
```

---

## ⚡ 快速开始

### 1. 环境要求

| 项目 | 版本要求 |
|------|----------|
| Python | **3.10+** |
| macOS | Apple Silicon (MPS 加速支持) |
| 虚拟环境 | venv / conda |

### 2. 克隆并创建虚拟环境

```bash
# 进入项目目录
cd ailearning

# 创建并激活虚拟环境（推荐使用 agent_env）
python -m venv agent_env
source agent_env/bin/activate   # macOS/Linux
# agent_env\Scripts\activate    # Windows

# 安装核心依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env，填入你的 API Key
```

`.env` 配置说明：

```ini
# ===== 必填 =====
OPENAI_API_KEY=sk-...               # OpenAI / DeepSeek / 兼容接口
OPENAI_API_BASE=https://api.openai.com/v1

# ===== 可选（按需填写） =====
DEEPSEEK_API_KEY=sk-...             # hybrid_rag / autogen_coder 使用
LANGCHAIN_API_KEY=ls-...            # LangSmith 全链路追踪
LANGCHAIN_TRACING_V2=true          # 开启追踪
LANGCHAIN_PROJECT=ailearning        # 项目名称
```

### 4. 验证安装

```bash
python -c "import langchain, langgraph, openai, chromadb; print('✅ 环境安装成功')"
```

### 5. 🚀 启动核心全栈知识库系统 (Frontend + Backend)

本项目内置了一套开箱即用的**企业级全栈 RAG 智能体系统**，采用前后端分离架构，支持混合检索、会话隔离和 LangGraph 循环反思。

**终端 1：启动 AI 后端引擎 (FastAPI + Hybrid RAG)**
```bash
# 进入后端目录
cd backend
pip install -r requirements.txt

# 启动引擎（首次启动会自动扫描项目内所有 .md 建立本地向量库，并在后台加载 BGE 重排模型）
python main.py
# 成功标志：看到 Uvicorn running on http://0.0.0.0:8000
```

**终端 2：启动交互前端 (Vite + React)**
```bash
# 进入前端目录
cd frontend
npm install

# 启动 Web 服务
npm run dev
# 成功标志：访问 http://localhost:5173/，右上角显示“已连接至麓谷 AI 节点”
```

---

## 📦 技术栈总览

| 类别 | 技术 | 版本/说明 |
|------|------|-----------|
| **LLM 框架** | LangChain · LangGraph | 链式调用 · 有状态 Agent 编排 |
| **多 Agent** | AutoGen v0.4 | 多智能体对话 · 代码执行沙箱 |
| **模型接入** | OpenAI SDK | GPT-4o · DeepSeek · 本地 Ollama |
| **标准协议** | MCP (Model Context Protocol) | AI 工具标准化连接 |
| **向量数据库** | ChromaDB · FAISS | 本地持久化向量存储 |
| **RAG 技术** | BM25 · MMR · CrossEncoder Rerank | 混合检索 · 精排优化 |
| **Embedding** | sentence-transformers · text-embedding-3 | 语义向量化 |
| **多模态** | Vision API · CLIP | 图片/视频理解 |
| **评估** | Ragas · LangSmith | RAG 质量评估 · 全链路追踪 |
| **Web 框架** | FastAPI · Uvicorn | 高性能异步 API |
| **ORM** | SQLAlchemy + Alembic | 数据库操作 · Schema 迁移 |
| **任务队列** | Celery + Redis | 异步任务 · 定时调度 |
| **模型原理** | Transformers · LoRA · vLLM | 推理 · 微调 · 优化 |
| **数据验证** | Pydantic v2 | 结构化输出 · 类型校验 |

---

## 📚 模块目录

### `01-prompt-engineering/` · Prompt 工程

> **核心思想**：利用大模型的上下文学习（In-context Learning）能力，通过输入提示对齐任务意图，无需修改模型参数。

**安装依赖**
```bash
pip install langchain langchain-openai python-dotenv
```

**运行示例**
```bash
# 思维链推理
python 01-prompt-engineering/03_chain_of_thought.py

# Few-shot vs CoT 对比实验
python 01-prompt-engineering/05_few_shot_vs_cot_comparison.py

# 企业级 Prompt 框架
python 01-prompt-engineering/prompt_framework.py

# DSPy 自动化 Prompt 优化
python 01-prompt-engineering/dspy_emotion_analysis.py
```

**关键文件**

| 文件 | 说明 |
|------|------|
| `01_basic_prompts.py` | 系统提示词、角色设定 |
| `02_prompt_templates.py` | `ChatPromptTemplate` 动态模板 |
| `03_chain_of_thought.py` | CoT 思维链推理 |
| `04_few_shot_prompts.py` | 少样本学习 |
| `05_few_shot_vs_cot_comparison.py` | 策略对比实验 |
| `prompt_framework.py` | 企业级 Prompt 框架封装 |
| `dspy_emotion_analysis.py` | DSPy 自动优化 |

---

### `02-function-calling/` · 工具调用

> **核心思想**：模型输出结构化 JSON 工具请求，外部环境执行具体动作，赋予 LLM 调用外部 API 的能力。

**安装依赖**
```bash
pip install openai pydantic python-dotenv
```

**运行示例**
```bash
python 02-function-calling/01_basic_function_calling.py
python 02-function-calling/pydantic_intro.py
```

**关键文件**

| 文件 | 说明 |
|------|------|
| `01_basic_function_calling.py` | 工具定义、JSON Schema、模型绑定、多工具调用 |
| `pydantic_intro.py` | Pydantic 结构化输出校验 |

---

### `03-mcp/` · Model Context Protocol

> **核心思想**：MCP 是 AI 与外部数据源/工具的标准化连接协议，类似 AI 界的 USB-C，实现 Server/Client 架构统一工具调用标准。

**安装依赖**
```bash
pip install mcp
```

**运行示例**
```bash
# 运行基础 MCP 客户端（自动启动 Server）
python 03-mcp/02_simple_client.py

# 企业级 MCP 服务
python 03-mcp/03_enterprise_mcp_server.py
```

**关键文件**

| 文件 | 说明 |
|------|------|
| `01_simple_server.py` | MCP Server：暴露资源(memo://)、工具(get_weather)、提示词模板 |
| `02_simple_client.py` | MCP Client：连接并调用服务端功能 |
| `03_enterprise_mcp_server.py` | 企业级多工具 MCP 服务 |
| `04_full_mcp_server.py` | 完整功能 MCP 服务（含认证） |
| `MCP_ENTERPRISE_BEST_PRACTICES.md` | 企业最佳实践文档 |

---

### `04-rag/` · 检索增强生成

> **核心思想**：Load → Split → Embed → Store → Retrieve → Generate，为 LLM 挂载外部知识库，解决幻觉和知识时效问题。

**安装依赖**
```bash
pip install langchain langchain-openai chromadb faiss-cpu rank_bm25 sentence-transformers tiktoken
```

**运行示例**
```bash
# 基础 RAG 流水线
python 04-rag/01_basic_rag.py

# 分块策略实验（chunk_size / overlap 对比）
python 04-rag/02_chunking_experiment.py

# MMR 多样性检索实验
python 04-rag/03_mmr_experiment.py

# BM25 关键词检索
python 04-rag/bm25.py

# 混合检索（语义 + 关键词 + Rerank）
python 04-rag/hybrid_retrieval_demo.py

# 交叉编码器精排
python 04-rag/rerank_demo.py

# 企业级完整流水线
python 04-rag/enterprise_rag_pipeline.py
```

**分块参数建议**

| 参数方案 | chunk_size | overlap | 适用场景 |
|----------|-----------|---------|----------|
| 精细检索 | 200 | 20 | 问答型 RAG |
| 标准推荐 | 500 | 50 | ✅ 通用场景 |
| 长文档 | 1000 | 100 | 报告分析 |

**关键文档**

| 文档 | 说明 |
|------|------|
| `ENTERPRISE_RAG_ARCHITECTURE.md` | 企业级 RAG 架构设计 |
| `HYBRID_RETRIEVAL.md` | BM25 + 向量混合检索策略 |
| `RERANK_STRATEGY.md` | CrossEncoder 精排方案 |
| `TEXT_CHUNKING_STRATEGIES.md` | 分块策略详解 |

---

### `05-embedding/` · 向量化

> **核心思想**：理解文本的数学表示，掌握语义相似度计算的底层逻辑（RAG 检索的基石）。

**安装依赖**
```bash
pip install sentence-transformers openai numpy
```

**运行示例**
```bash
# 余弦相似度计算实验
python 05-embedding/01_cosine_similarity.py

# 不同 Embedding 模型对比
python 05-embedding/02_model_comparison.py
```

---

### `06-agent-basics/` · Agent 基础（LangGraph）

> **核心思想**：将 Agent 构建为有状态的状态机（Finite State Machine），通过维护全局 State 在不同 Node 之间流转，解决传统链条无法处理反馈和复杂分支的问题。

**安装依赖**
```bash
pip install langgraph langchain langchain-openai
```

**运行示例**
```bash
# 基础 StateGraph Agent
python 06-agent-basics/01_simple_langgraph_agent.py

# 工具集成 Agent（RAG + MCP）
python 06-agent-basics/02_integrated_agent.py

# Agent + 记忆系统
python 06-agent-basics/03_agent_memory.py

# 多 Agent 协作（研究员 + 写手）
python 06-agent-basics/04_multi_agent_collaboration.py
```

**关键概念**

```python
from langgraph.graph import StateGraph, MessagesState, START, END

builder = StateGraph(MessagesState)
builder.add_node("llm_call", llm_call)        # 节点
builder.add_node("tool_node", tool_node)
builder.add_edge(START, "llm_call")            # 边
builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])  # 条件路由
builder.add_edge("tool_node", "llm_call")      # 循环回路
agent = builder.compile()
```

---

### `07-advanced-memory/` · Agent 深度记忆

> **核心思想**：没用的闲聊 → 摘要化丢弃；重要事实 → 向量化入库；需要时 → RAG 唤醒注入提示词。

**安装依赖**
```bash
pip install langgraph langchain chromadb
```

**运行示例**
```bash
# 摘要记忆（解决 Token 爆炸）
python 07-advanced-memory/01_summary_memory.py

# 长效用户画像（跨会话持久化）
python 07-advanced-memory/02_long_term_profile.py
```

**记忆分层架构**

| 层级 | 存储位置 | 生命周期 | 技术实现 |
|------|----------|----------|----------|
| 瞬时状态 | AgentState.messages | 当前轮次 | LangGraph State |
| 短期记忆 | 压缩摘要 | 当前会话 | `RemoveMessage` + Summary |
| 长期记忆 | ChromaDB 向量库 | 永久持久 | `save_user_fact` Tool |

---

### `08-multimodal/` · 多模态 RAG

> **核心思想**：全媒介信息向量化，实现"看图/看视频"检索与理解。

**安装依赖**
```bash
pip install openai pillow
```

**运行示例**
```bash
# Vision API 图片理解测试
python 08-multimodal/01_test_vision.py
```

**参考文档**

| 文档 | 说明 |
|------|------|
| `PRINCIPLES.md` | 多模态 RAG 设计原则（CLIP · Captioning · 联合嵌入） |
| `VIDEO_RAG.md` | 视频时序检索方案（关键帧提取 · 时间戳索引） |

---

### `09-evaluation/` · 评估与可观测性

> **核心思想**：让强模型给弱模型的回答打分（LLM-as-a-judge），科学定位系统瓶颈（搜不到 vs 瞎编）。

**安装依赖**
```bash
pip install ragas langchain-openai datasets
```

**运行示例**
```bash
# Ragas 模拟评测（无需真实数据）
python 09-evaluation/01_ragas_simulation.py

# 真实 Ragas 完整评估流水线
python 09-evaluation/02_real_ragas.py

# 效果归因分析（定位瓶颈）
python 09-evaluation/effect_attribution.py
```

**Ragas 四大核心指标**

| 指标 | 定义 | 诊断问题 |
|------|------|----------|
| **Faithfulness** | 答案是否忠实于检索内容 | 检测幻觉 |
| **Answer Relevance** | 答案是否回答了问题 | 检测跑题 |
| **Context Precision** | 检索内容是否精准 | 检测噪声 |
| **Context Recall** | 关键信息是否被召回 | 检测遗漏 |

**LangSmith 配置（可选）**
```ini
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ailearning-eval
```

---

### `10-production/` · 生产级实战

> **核心思想**：通过状态持久化实现长连接对话，通过强制中断点（interrupt_before）确保高风险操作的可控性。

**运行示例**
```bash
# RepoSense HITL 完整版（含人机协同审批）
python projects/repo_sense/assistant_v4_hitl.py

# 生产稳定性测试（重试 · 限流 · 降级）
python 10-production/01_production_stability.py
```

**生产级关键能力**

| 能力 | 技术实现 | 说明 |
|------|----------|------|
| 流式输出 | `stream()` / `astream()` | 降低首 Token 延迟 |
| 断点续传 | `MemorySaver` Checkpointer | 服务重启后恢复 |
| 人机审批 | `interrupt_before=["execute"]` | 高风险操作前暂停 |
| 指数退避 | `tenacity` 库 | API 限流自动重试 |
| 语义缓存 | `SemanticCache` | 相似问题复用答案 |

---

## 🏛️ 板块四：企业级 AI 生产底座与全栈工程基建 (11-15)

> 💡 **架构师认知**：为什么 AI 工程师必须掌握 11-15？  
> 很多初学者误以为 12-15 只是“重复安装普通 Web 后端依赖”。**这是从“单机玩具 Demo”迈向“工业级生产系统”的决定性护城河**！  
> - 大模型推理耗时通常达数十秒，若直接在 HTTP 中同步等待会导致前端 504 网关超时雪崩 → 必须用 **14-Celery** 异步解耦、429 指数退避与多 Agent 并行调度；  
> - Agent 的思考轨迹（Checkpoint）、用户个性化长期记忆、Token 计费与人机审批状态断电即丢 → 必须用 **13-SQLAlchemy** 异步 ORM 持久化至关系数据库；  
> - 高并发环境下的大模型 GPU 显存生命周期预热、ChatGPT 式 SSE 实时打字机推流与鉴权审计 → 必须用 **12-FastAPI**；  
> - **15-agent-architecture** 则将 12、13、14 与 Agent 状态机融会贯通，提供真实可运行的端到端全栈协同系统闭环！

### `11-python-advanced/` · Python 高性能进阶

**运行示例**
```bash
python 11-python-advanced/advanced_python_demo.py  # 装饰器 · 生成器 · 异步事件循环 · 元类
python 11-python-advanced/dataclass_demo.py        # Dataclass 数据建模与序列化
```

---

### `12-fastapi-advanced/` · 大模型高性能 API 网关与 SSE 流式输出

> **核心思想**：利用 FastAPI 原生异步机制与 Starlette 底座，实现 GPU 显存预热加载、实时打字机推流与企业级依赖注入树。

**安装依赖**
```bash
pip install fastapi uvicorn[standard] httpx pydantic websockets
```

**运行示例**
```bash
# 1. 启动 AI 高性能网关服务（含 Lifespan 模型显存预热与中间件全链路耗时监控）
uvicorn 12-fastapi-advanced.app:app --reload --port 8080

# 2. 测试 SSE 流式打字机逐 Token 推流接口
curl -N -X POST http://127.0.0.1:8080/generate_report \
  -H "Authorization: Bearer secret_admin_token" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "请深度解析 Agent 架构", "stream": true}'

# 3. 运行接口自动化验证套件
pytest 12-fastapi-advanced/test_fastapi_examples.py -v
```

**覆盖技术**：Lifespan 显存管理 · SSE 打字机流式推流 · 嵌套 Depends 鉴权树 · 链路打点中间件 · WebSocket 交互

---

### `13-sqlalchemy-advanced/` · 智能体状态持久化与用户记忆资产

> **核心思想**：向量库无法替代关系型数据库。利用 SQLAlchemy 2.0 异步 ORM 实现 Agent 对话 Checkpoint 落盘、Token 账单审计与连接池防雪崩。

**安装依赖**
```bash
pip install sqlalchemy aiosqlite greenlet alembic
```

**运行示例**
```bash
# 1. 运行异步 ORM 实战（演示连接池预探活 pool_pre_ping、级联绑定与 selectinload 解决 N+1）
python 13-sqlalchemy-advanced/advanced_orm.py

# 2. 查看生产级数据库 Schema 版本迁移指南 (Alembic)
cat 13-sqlalchemy-advanced/ALEMBIC_GUIDE.md
```

**覆盖技术**：SQLAlchemy 2.0 异步驱动 · `pool_pre_ping` 长连接保活 · 任务与步骤轨迹级联映射 · `selectinload` / `joinedload` 查询优化 · Alembic 异步迁移

---

### `14-celery-advanced/` · 大模型长耗时任务解耦与多 Agent 分布式编排

> **核心思想**：彻底解耦 Web 接入层与慢推理计算层。利用 Celery 解决长耗时推理超时、API 429 频率超限自动重试、多 SubAgent 并行 Map-Reduce 编排与知识库定时同步。

**安装依赖**
```bash
pip install celery redis
brew services start redis   # 启动 Redis 作为 Broker 与 Backend
```

**运行示例**
```bash
# 1. 启动 Celery Worker 监听 AI 任务队列（独立终端运行）
celery -A 14-celery-advanced.celery_app worker --loglevel=info --concurrency=4

# 2. 运行客户端调度演示（包含 429 自适应指数退避、多 Agent 并行 Chord 搜集、向量库定时同步）
python 14-celery-advanced/tasks.py

# 3. （可选）启动 Celery Beat 定时调度引擎
celery -A 14-celery-advanced.celery_app beat --loglevel=info
```

**覆盖技术**：Celery + Redis 分布式集群 · 429 智能指数退避 (`countdown=2^n`) · `chord` 原语并行汇聚 · Beat Cronjob 知识库自动更新

---

### `15-agent-architecture/` · 企业级全栈 Agent 架构协同实战

> **核心思想**：拒绝纸上谈兵，将 12-FastAPI（接口/SSE）、13-SQLAlchemy（轨迹持久化/记账）、14-Celery（异步长思考）与 LangGraph 状态机融会贯通，提供端到端完整生产闭环！

**运行示例**
```bash
# 模式一：开箱即用单脚本自测（直接在控制台跑通 任务接入 -> 数据库落盘 -> 后台Worker状态机 -> SSE推流 -> 数据库回读闭环）
python 15-agent-architecture/full_stack_agent_system.py

# 模式二：作为独立 API 服务启动与 curl 交互
uvicorn 15-agent-architecture.full_stack_agent_system:app --reload --port 8090

# 模式三：深度研读企业级 Agent 白皮书（安全沙箱隔离、递归深度控制、上下文噪声过滤）
cat 15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md
```

**覆盖技术**：FastAPI+Celery+SQLAlchemy 端到端全栈协同 · 多步骤状态机推理流 (PLAN->SEARCH->CRITIC->SUMMARY) · 全链路 Token 记账与审计 · SSE 实时事件总线 · 企业级架构白皮书

---

### `16-face-recognition/` · 人脸识别

**安装依赖**
```bash
pip install insightface fastapi uvicorn onnxruntime
python 16-face-recognition/download_weights.py   # 下载模型权重
```

**运行示例**
```bash
# 启动人脸识别 API 服务
uvicorn 16-face-recognition.face_api:app --port 8001

# 运行准确率评测
python 16-face-recognition/test_accuracy.py
```

---

### `17-transformers-basics/` · Transformer 原理与优化

> 从 Tokenizer 到 LoRA 微调，从 KV Cache 到 vLLM，理解大模型底层机制。Mac MPS 硬件加速适配。

**安装依赖**
```bash
pip install -r 17-transformers-basics/requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**运行示例（推荐顺序）**
```bash
python 17-transformers-basics/01_tokenizer_basics.py     # Tokenizer 原理
python 17-transformers-basics/02_embedding_rag.py        # BGE Embedding 本地运行
python 17-transformers-basics/03_local_llm_inference.py  # 本地 LLM 推理（0.5B 模型）
python 17-transformers-basics/04_attention_basics.py     # 注意力机制实现
python 17-transformers-basics/06_transformer_block.py    # Transformer Block
python 17-transformers-basics/07_lora_finetuning.py      # LoRA 参数高效微调
python 17-transformers-basics/08_kv_cache_inference.py   # KV Cache 推理加速
python 17-transformers-basics/14_rlhf_dpo_alignment.py   # RLHF/DPO 对齐
```

**关键技术点**

| 文件 | 技术 | 核心价值 |
|------|------|----------|
| `07_lora_finetuning.py` | **LoRA** | 仅训练 0.1% 参数完成微调 |
| `08_kv_cache_inference.py` | **KV Cache** | 避免重复计算，加速推理 |
| `09_moe_basics.py` | **MoE** | 稀疏激活，DeepSeek 核心架构 |
| `10_quantization_concepts.py` | **量化** | INT4/INT8 显存压缩 |
| `11_flash_attention_concept.py` | **Flash Attention** | IO 优化，加速长序列 |
| `14_rlhf_dpo_alignment.py` | **RLHF/DPO** | 对齐人类偏好 |
| `16_continuous_batching.py` | **连续批处理** | vLLM 核心原理 |

---

### `18-inference-serving/` · 高性能推理与部署架构

> **核心思想**：实现企业级吞吐量的低延迟、高并发大模型部署引擎，包括 vLLM、TensorRT-LLM、Triton Inference Server、量化等。

---

### `19-model-finetuning/` · 大模型微调实战

> **核心思想**：通过 SFT（指令微调）与 RLHF/DPO 注入专属垂直领域知识，打造企业专属领域小模型。

---

### `20-graph-rag/` · 知识引擎与高阶 RAG

> **核心思想**：引入图结构数据表达复杂实体关系，实现多跳逻辑推理，以及 Agentic RAG。

---

### `21-multi-agent-scale/` · 复杂多智能体协同

> **核心思想**：面向企业复杂工作流的群体智能编排，自动纠错与大规模协同。学习 CrewAI / Swarm 等分层架构。

---

### `22-ai-security/` · AI 安全与红蓝对抗

> **核心思想**：提示词注入攻击防御、Agent 沙箱安全隔离及细粒度 RBAC 鉴权机制。

---

### `23-edge-ai/` · 端侧与异构计算

> **核心思想**：在 Apple Silicon 等边缘侧设备上实现超低延迟的私密部署（MLX、ONNX、CoreML）。

---

### `examples/` · 独立示例脚本

> 该目录包含各种单文件直接可运行的集成示例和工具集，非常适合作为速查参考库。

**运行示例**
```bash
# 高级 RAG 架构测试（包含检索、生成和简易评估）
python examples/advanced_rag_demo.py

# MySQL 智能查询 Agent（Text-to-SQL）
python examples/mysql_agent.py

# Reranker 重排序演示
python examples/reranker_demo.py

# 数据库清理工具示例
python examples/batch_delete_tool.py
```

**关键文件说明**
- `advanced_rag_demo.py`: RAG 整合演示。
- `high_accuracy_agent_demo.py`: 高可用度 Agent 原型。
- `mysql_agent.py`: 结合关系型数据库的查询智能体。
- `batch_delete_tool.py` / `delete_atnd_his.py`: 数据库及数据清洗运维自动化脚本。

---

## 🚀 实战项目

### 1. RepoSense · 代码仓库智能助手

**路径**：[`projects/repo_sense/`](./projects/repo_sense/)  
**技术栈**：LangGraph · ChromaDB · HITL · MemorySaver

```
核心能力：
  ✅ 代码仓库向量化索引（ChromaDB）
  ✅ 自然语言代码检索
  ✅ LangGraph [规划-执行-验证] 状态机
  ✅ 多文件批量修改
  ✅ HITL 人机协同审批（interrupt_before）
  ✅ 断点续传（Checkpoint 恢复）
```

**运行**
```bash
# 先建立代码索引
python projects/repo_sense/indexer.py

# 启动带 HITL 的完整助手
python projects/repo_sense/assistant_v4_hitl.py
```

---

### 2. hybrid_rag · 企业级混合检索系统

**路径**：[`hybrid_rag/`](./hybrid_rag/)  
**技术栈**：BM25 · ChromaDB · RRF · CrossEncoder · FastAPI · DeepSeek

```
检索架构：
  用户问题
    ├──► BM25 关键字检索（jieba 分词）──────┐
    └──► ChromaDB 向量语义检索 ──► RRF 融合 ──► CrossEncoder 精排 ──► LLM 生成
```

**安装依赖**
```bash
source agent_env/bin/activate
pip install -r hybrid_rag/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**配置**
```ini
# .env
DEEPSEEK_API_KEY=sk-...
OPENAI_API_BASE=https://api.deepseek.com/v1
```

**启动**
```bash
# 方式一：一键启动
bash hybrid_rag/start.sh

# 方式二：手动启动
uvicorn hybrid_rag.app:app --host 0.0.0.0 --port 8000 --reload
```

**访问**
- Web UI：http://localhost:8000
- API 文档：http://localhost:8000/docs

**API 示例**
```bash
# 混合检索
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "BM25算法原理", "top_k": 5}'

# RAG 问答
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是混合检索？"}'

# 添加文档
curl -X POST http://localhost:8000/api/documents/add \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"content": "你的文档内容...", "metadata": {"category": "技术"}}]}'
```

---

### 3. document_processor · 多格式文档解析器

**路径**：[`document_processor/`](./document_processor/)  
**技术栈**：PyMuPDF · python-docx · pandas · openpyxl

**安装依赖**
```bash
# ⚠️ 注意：必须安装 pymupdf，不要安装 fitz（假包）
pip install pymupdf python-docx pandas openpyxl tabulate
```

**运行**
```bash
cd document_processor

# 生成测试数据
python generate_samples.py

# 运行解析器
python doc_parser.py
```

**代码接入**
```python
from document_processor.doc_parser import DocumentProcessor

parser = DocumentProcessor(chunk_size=500)

# 支持 PDF / Word / Excel 自动路由
chunks = parser.process_file("your_document.pdf")

# 输出格式与向量数据库无缝对接
for chunk in chunks:
    print(chunk["metadata"])  # {'source': '...', 'type': 'pdf', 'page': 1}
    print(chunk["content"])   # 分块纯文本

# 直接接入 hybrid_rag
engine.add_documents(chunks)
```

**⚠️ 踩坑记录**
> `import fitz` 报错 → 先执行 `pip uninstall -y fitz`，再 `pip install pymupdf`

---

### 4. autogen_coder · 自动化代码 Agent

**路径**：[`autogen_coder/`](./autogen_coder/)  
**技术栈**：AutoGen v0.4 · DeepSeek · LocalCommandLineCodeExecutor

```
工作流：AssistantAgent（写代码）→ UserProxyAgent（沙箱执行）→ 报错自动修复循环
```

**安装依赖**
```bash
pip install pyautogen
```

**配置**
```bash
export DEEPSEEK_API_KEY="sk-..."
```

**运行**
```bash
python autogen_coder/coder_agent.py
```

> 运行时会自动创建 `workspace/` 沙箱目录，防止 Agent 修改宿主机文件。

---

## 📖 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **🖥️ 产品演示交互 PPT** | [product_presentation.html](./product_presentation.html) | **基于 Reveal.js 的沉浸式产品设计氛围引导幻灯片** |
| **🔐 多租户账号与权限手册** | [ACCOUNTS.md](./ACCOUNTS.md) | **预置体验账号密码、最高管理员凭证与 RBAC 权限维护指南** |
| **产品交付落地路线图** | [DELIVERY_ROADMAP.md](./docs/DELIVERY_ROADMAP.md) | **生产交付标准、待推进工程清单与版本演进排期** |
| **产品开发文档 (PRD)** | [PRODUCT_SPEC.md](./docs/PRODUCT_SPEC.md) | 通俗易懂讲透项目背景、设计、用户、痛点与终极目标 |
| 产品设计白皮书 | [PRODUCT_DESIGN_WHITE_PAPER.md](./docs/PRODUCT_DESIGN_WHITE_PAPER.md) | 产品背景、技术架构、面向用户、产品价值与未来演进 |
| 技术全景目录 | [TECH_OVERVIEW.md](./TECH_OVERVIEW.md) | AI 架构师视角的技术汇总 |
| 项目学习路径 | [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) | 10 阶段学习精华 |
| Agent 开发指南 | [agent_dev_guide.md](./agent_dev_guide.md) | Agent 完整开发手册 |
| 企业 RAG 架构 | [04-rag/ENTERPRISE_RAG_ARCHITECTURE.md](./04-rag/ENTERPRISE_RAG_ARCHITECTURE.md) | RAG 架构设计 |
| Agent 白皮书 | [15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md](./15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md) | 企业级 Agent 架构 |
| Transformer 摘要 | [17-transformers-basics/SUMMARY.md](./17-transformers-basics/SUMMARY.md) | 模型原理技术总结 |
| 可观测性方案 | [09-evaluation/OBSERVABILITY_AND_EVALUATION.md](./09-evaluation/OBSERVABILITY_AND_EVALUATION.md) | 评估与监控 |
| hybrid_rag 说明 | [hybrid_rag/README.md](./hybrid_rag/README.md) | 混合检索系统完整文档 |
| 文档解析器说明 | [document_processor/README.md](./document_processor/README.md) | 多格式解析踩坑记录 |

---

## 🗺️ 推荐学习路线

```
阶段一（1-2周）基础交互
  01 Prompt 工程 → 02 Function Calling → 03 MCP 协议

阶段二（2-3周）知识系统
  04 RAG 检索 → 05 Embedding → document_processor 实战

阶段三（2-3周）Agent 编排
  06 LangGraph Agent → 07 深度记忆 → 06/多 Agent 协作

阶段四（1-2周）多模态与原理
  08 多模态 RAG → 17 Transformer 原理（选学 LoRA/量化）

阶段五（持续迭代）生产与评估
  09 Ragas 评估 → 10 HITL 生产 → RepoSense / hybrid_rag 综合实战
```

---

> **环境说明**：所有实验均在 macOS (Apple Silicon) 下验证通过，Transformers 相关脚本已适配 MPS 加速。  
> **模型兼容**：除特别说明外，所有脚本同时兼容 OpenAI GPT-4o、DeepSeek、本地 Ollama 等兼容 OpenAI 接口的模型。

---

## 🎯 总结与寄语

AI 工程化已经从“套壳 API 调用”进化到了 **Agentic Workflow（智能体工作流）** 与 **全栈可观测性** 时代。
通过本仓库的学习与沉淀：
- 你将不再仅仅会写 Prompt，而是懂得如何利用 **LangGraph 构建可靠的状态机闭环**；
- 你将不再满足于简单的 Vector Store 检索，而是懂得 **BM25 + 向量召回 + Rerank 重排的工业级架构**；
- 你将理解大模型底层的 **注意力机制、KV Cache 与 微调原理**，从而在遇到模型推理性能瓶颈时游刃有余；
- 最终，你将具备通过 **MCP 标准协议**和 **生产级工程设计**（异步、限流、熔断）将 AI 无缝接入现有企业系统架构的能力。

**Happy Coding! 🚀 让 AI 真正落地产生价值。**
