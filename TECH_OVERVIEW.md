# 🏗️ AI 工程项目 · 技术全景目录

> **定位**：AI 架构师视角 · 从基础能力到生产部署的完整技术图谱  
> **更新**：2026-07 · 基于项目实际代码结构整理

---

## 📐 整体架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    🎯 生产级 AI 应用层                        │
│         RepoSense · hybrid_rag · document_processor          │
├─────────────────────────────────────────────────────────────┤
│                    🤖 Agent 编排层                            │
│       LangGraph · AutoGen · Multi-Agent · HITL               │
├─────────────────────────────────────────────────────────────┤
│                    🧠 AI 能力层                               │
│   RAG · Embedding · Multimodal · Memory · Evaluation         │
├─────────────────────────────────────────────────────────────┤
│                    🔧 基础工程层                              │
│    FastAPI · SQLAlchemy · Celery · MCP · Pydantic            │
├─────────────────────────────────────────────────────────────┤
│                    📡 模型与协议层                            │
│   OpenAI SDK · LangChain · Transformers · Function Calling   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 技术栈全景

| 类别 | 技术 | 用途 |
|------|------|------|
| **LLM 框架** | LangChain · LangGraph | 链式调用、有状态 Agent 编排 |
| **多 Agent** | AutoGen · LangGraph Multi-Agent | 多智能体协作、代码执行 Agent |
| **模型协议** | OpenAI SDK · MCP | API 调用、标准化工具连接 |
| **向量数据库** | ChromaDB · FAISS | 文档向量存储与检索 |
| **RAG 技术** | BM25 · MMR · Rerank | 混合检索、精排优化 |
| **Embedding** | text-embedding-3-small/large | 文本向量化、语义相似度 |
| **多模态** | Vision API · CLIP | 图片理解、视频检索 |
| **评估框架** | Ragas · LangSmith | RAG 质量评估、全链路追踪 |
| **Web 框架** | FastAPI | 高性能异步 API 服务 |
| **ORM** | SQLAlchemy + Alembic | 数据库操作、Schema 迁移 |
| **任务队列** | Celery | 异步任务、分布式计算 |
| **AI 推理** | Transformers · LoRA · vLLM | 本地模型推理、微调 |
| **数据验证** | Pydantic | 结构化输出、数据校验 |
| **语言** | Python 3.10+ | 全栈 AI 开发 |

---

## 📚 学习模块目录

### 🔵 第一层：模型交互基础

#### `01-prompt-engineering/` · Prompt 工程
> **核心价值**：掌握 LLM 的"语言"，是一切 AI 应用的起点

| 文件 | 技术要点 |
|------|----------|
| `01_basic_prompts.py` | 系统提示词、角色设定 |
| `02_prompt_templates.py` | `ChatPromptTemplate` 模板化 |
| `03_chain_of_thought.py` | 思维链（CoT）推理 |
| `04_few_shot_prompts.py` | 少样本学习（Few-shot） |
| `05_few_shot_vs_cot_comparison.py` | Few-shot vs CoT 效果对比 |
| `prompt_framework.py` | 企业级 Prompt 框架封装 |
| `dspy_emotion_analysis.py` | DSPy 自动化 Prompt 优化 |
| `model_routing/` | 多模型路由策略 |
| `prompt_management/` | Prompt 版本管理 |

**关键技术**：In-context Learning · CoT · Few-shot · DSPy · Prompt 版本化

---

#### `02-function-calling/` · 工具调用
> **核心价值**：让 LLM 具备"手"，能调用外部工具和 API

| 文件 | 技术要点 |
|------|----------|
| `01_basic_function_calling.py` | 工具定义、JSON Schema、模型绑定 |
| `pydantic_intro.py` | Pydantic 结构化输出校验 |

**关键技术**：Function Calling · Pydantic · JSON Schema · Tool Binding

---

#### `03-mcp/` · Model Context Protocol
> **核心价值**：AI 与数据源/工具的标准化连接协议（类似 AI 界的 USB-C）

| 文件 | 技术要点 |
|------|----------|
| `01_simple_server.py` | MCP Server 实现 |
| `02_simple_client.py` | MCP Client 接入 |
| `03_enterprise_mcp_server.py` | 企业级 MCP 服务 |
| `04_full_mcp_server.py` | 完整功能 MCP 服务 |
| `MCP_ENTERPRISE_BEST_PRACTICES.md` | 企业最佳实践文档 |

**关键技术**：MCP Server/Client · stdio/SSE 传输 · 工具标准化 · 资源暴露

---

### 🟢 第二层：知识与记忆

#### `04-rag/` · 检索增强生成（RAG）
> **核心价值**：为 LLM 挂载外部知识库，解决幻觉和知识时效问题

| 文件/文档 | 技术要点 |
|-----------|----------|
| `01_basic_rag.py` | 基础 RAG 流水线 |
| `02_chunking_experiment.py` | 文本分块策略实验 |
| `03_mmr_experiment.py` | MMR 多样性检索 |
| `bm25.py` | BM25 关键词检索 |
| `hybrid_retrieval_demo.py` | **混合检索**（语义 + 关键词） |
| `rerank_demo.py` | **交叉编码器精排** |
| `enterprise_rag_pipeline.py` | 企业级 RAG 完整流水线 |
| `document_parsing_pipeline.py` | 多格式文档解析 |
| `ENTERPRISE_RAG_ARCHITECTURE.md` | 架构设计文档 |
| `HYBRID_RETRIEVAL.md` | 混合检索策略详解 |
| `RERANK_STRATEGY.md` | Rerank 策略详解 |

**关键技术**：ChromaDB · FAISS · BM25 · MMR · Rerank · 文本分块 · 文档解析

---

#### `05-embedding/` · Embedding 向量化
> **核心价值**：理解文本的数学表示，掌握语义相似度计算原理

| 文件 | 技术要点 |
|------|----------|
| `01_cosine_similarity.py` | 余弦相似度计算 |
| `02_model_comparison.py` | 不同 Embedding 模型对比 |

**关键技术**：向量空间 · 余弦相似度 · Embedding 模型选型

---

#### `07-advanced-memory/` · Agent 深度记忆
> **核心价值**：模拟人类短期 + 长期记忆，突破上下文窗口限制

| 文件 | 技术要点 |
|------|----------|
| `01_summary_memory.py` | **摘要记忆**：压缩历史对话 |
| `02_long_term_profile.py` | **长效用户画像**：跨会话持久化 |

**关键技术**：摘要压缩 · 用户画像 · SQLite 持久化 · 记忆分层架构

---

### 🟡 第三层：Agent 编排

#### `06-agent-basics/` · Agent 基础（LangGraph）
> **核心价值**：将 Agent 构建为可控的有状态状态机

| 文件 | 技术要点 |
|------|----------|
| `01_simple_langgraph_agent.py` | StateGraph 基础图构建 |
| `02_integrated_agent.py` | 工具集成 Agent |
| `03_agent_memory.py` | Agent + 记忆系统 |
| `04_multi_agent_collaboration.py` | **多 Agent 协作** |
| `react_agent/` | ReAct 推理模式实现 |
| `complex_workflow/` | 复杂分支工作流 |

**关键技术**：StateGraph · Node/Edge · 条件路由 · ReAct · 多 Agent 通信

---

#### `autogen_coder/` · AutoGen 代码 Agent
> **核心价值**：基于微软 AutoGen 框架的自动化代码生成 Agent

| 文件 | 技术要点 |
|------|----------|
| `coder_agent.py` | AssistantAgent + CodeExecutorAgent |

**关键技术**：AutoGen v0.4 · RoundRobinGroupChat · 代码执行沙箱 · 终止条件

---

#### `15-agent-architecture/` · 企业级 Agent 架构
> **核心价值**：生产级 Agent 的白皮书级架构设计

| 文件 | 技术要点 |
|------|----------|
| `ENTERPRISE_AGENT_WHITEPAPER.md` | 架构原则、安全边界、部署策略 |

**关键技术**：Agent 安全 · 工具权限控制 · 可观测性 · 成本治理

---

### 🟠 第四层：多模态与模型原理

#### `08-multimodal/` · 多模态 RAG
> **核心价值**：处理图片、图表及视频信息的检索与理解

| 文件/文档 | 技术要点 |
|-----------|----------|
| `01_test_vision.py` | Vision API 图片理解 |
| `PRINCIPLES.md` | 多模态 RAG 设计原则 |
| `VIDEO_RAG.md` | 视频时序检索方案 |

**关键技术**：Vision API · CLIP 联合 Embedding · 视频关键帧提取 · 多模态向量

---

#### `17-transformers-basics/` · Transformer 原理与优化
> **核心价值**：理解大模型底层机制，为精调与部署打基础

| 文件 | 技术要点 |
|------|----------|
| `01_tokenizer_basics.py` | Tokenizer 原理 |
| `04_attention_basics.py` | **注意力机制**实现 |
| `05_positional_encoding.py` | 位置编码（RoPE/ALiBi） |
| `06_transformer_block.py` | Transformer Block 完整实现 |
| `07_lora_finetuning.py` | **LoRA 参数高效微调** |
| `08_kv_cache_inference.py` | KV Cache 推理加速 |
| `09_moe_basics.py` | MoE 混合专家架构 |
| `10_quantization_concepts.py` | INT4/INT8 量化 |
| `11_flash_attention_concept.py` | Flash Attention 原理 |
| `12_decoding_strategies.py` | 解码策略（Beam/TopK/TopP） |
| `13_speculative_decoding.py` | 投机解码加速 |
| `14_rlhf_dpo_alignment.py` | **RLHF/DPO 对齐训练** |
| `15_structured_output_logits.py` | Logits 控制结构化输出 |
| `16_continuous_batching.py` | 连续批处理（vLLM 原理） |

**关键技术**：Attention · RoPE · LoRA · KV Cache · Flash Attention · MoE · RLHF · DPO

---

#### `16-face-recognition/` · 人脸识别
> **核心价值**：计算机视觉与 AI API 服务结合实战

| 文件 | 技术要点 |
|------|----------|
| `face_api.py` | FastAPI 人脸识别服务 |
| `test_accuracy.py` | 准确率评测 |
| `download_weights.py` | 模型权重管理 |

**关键技术**：InsightFace · FastAPI · 人脸向量化 · 相似度匹配

---

### 🔴 第五层：评估与生产

#### `09-evaluation/` · 评估与可观测性
> **核心价值**：科学量化 AI 系统质量，定位瓶颈

| 文件 | 技术要点 |
|------|----------|
| `01_ragas_simulation.py` | Ragas 模拟评测 |
| `02_real_ragas.py` | 真实 Ragas 评估流水线 |
| `effect_attribution.py` | 效果归因分析 |
| `OBSERVABILITY_AND_EVALUATION.md` | 可观测性全方案 |

**关键技术**：Ragas · LangSmith · 评估指标（Faithfulness / Relevance / Recall）· 效果归因

---

#### `10-production/` · 生产级稳定性
> **核心价值**：流式输出、容错、成本控制的生产最佳实践

| 文件 | 技术要点 |
|------|----------|
| `01_production_stability.py` | 重试、限流、降级策略 |
| `PRODUCTION_STABILITY.md` | 生产稳定性指南 |

**关键技术**：Streaming · 指数退避重试 · 语义缓存 · 成本监控 · 熔断器

---

### 🟣 第六层：企业级 AI 生产底座与全栈工程基建 (11-15)
> **核心价值**：跨越从“单机玩具 Demo”到“工业级生产系统”的鸿沟，提供高并发网关、状态持久化、长任务解耦与全栈协同闭环

#### `11-python-advanced/` · Python 高性能进阶

| 文件 | 技术要点 |
|------|----------|
| `advanced_python_demo.py` | 装饰器 · 生成器 · 异步事件循环 · 元类 |
| `dataclass_demo.py` | Dataclass 数据建模与序列化 |

#### `12-fastapi-advanced/` · 大模型高性能 API 网关与 SSE 流式输出

| 文件 | 技术要点 |
|------|----------|
| `app.py` | Lifespan 显存模型预热与释放 · SSE 流式打字机推流 · 嵌套 Depends 鉴权树 · 耗时监控中间件 |
| `more_fastapi_examples.py` | WebSocket 双向通信 · 流式分片文件上传 |
| `test_fastapi_examples.py` | API 异步集成测试与接口断言 |

**关键技术**：Lifespan 显存管理 · SSE 打字机流式 · 依赖注入 (Depends) · 全链路耗时打点 · WebSocket

#### `13-sqlalchemy-advanced/` · 智能体状态持久化与用户记忆资产

| 文件 | 技术要点 |
|------|----------|
| `advanced_orm.py` | SQLAlchemy 2.0 异步连接池 · `pool_pre_ping` 长连接保活 · 任务与步骤轨迹级联映射 · `selectinload` 解决 N+1 |
| `ALEMBIC_GUIDE.md` | Alembic 数据库 Schema 异步版本迁移指南 |

**关键技术**：SQLAlchemy 2.0 异步 ORM · 连接池防雪崩 · Agent Checkpoint 状态落盘 · Token 消耗记账 · 级联孤立清理

#### `14-celery-advanced/` · 大模型长耗时任务解耦与多 Agent 分布式编排

| 文件 | 技术要点 |
|------|----------|
| `celery_app.py` | Celery 实例初始化与 Redis Broker/Backend 配置 |
| `tasks.py` | AI 深度研报生成 · 大模型 429 智能指数退避 (`countdown=2^n`) · 多 SubAgent 并行搜集 (`chord` Map-Reduce) · 知识库定时索引 |
| `CELERY_AGENT_GUIDE.md` | Celery 与 LangGraph 生产融合指南 |

**关键技术**：分布式任务队列 · Redis Broker · 429 自适应指数退避 · Chord 原语并行汇聚 · Beat Cronjob 定时任务

#### `15-agent-architecture/` · 企业级全栈 Agent 架构协同实战

| 文件 | 技术要点 |
|------|----------|
| `full_stack_agent_system.py` | **端到端全栈协同系统**：FastAPI 网关接入 + SQLAlchemy 轨迹落盘 + 后台 Worker 状态机推理 (PLAN/SEARCH/CRITIC/SUMMARY) + SSE 实时推流 + 数据库回读验证 |
| `ENTERPRISE_AGENT_WHITEPAPER.md` | 企业级 Agent 落地白皮书：五大支柱、四大硬性要求、三大死亡难点（工具幻觉、死循环、上下文噪声）应对策略 |

**关键技术**：全栈架构协同 · 异步长任务解耦 · 状态机多阶段推理 · SSE 实时广播总线 · 审计追踪与账单中心

---

## 🚀 实战项目索引

### 1. RepoSense — 代码仓库智能助手
**路径**：[`projects/repo_sense/`](./projects/repo_sense/)

```
核心能力：
  ✅ 代码仓库向量化索引（ChromaDB）
  ✅ 自然语言代码检索
  ✅ LangGraph 状态机决策
  ✅ 多文件批量修改
  ✅ HITL 人机协同审批（Human-in-the-Loop）
  ✅ 断点续传（Checkpoint 恢复）

技术栈：LangGraph · ChromaDB · HITL · Checkpointer
```

### 2. hybrid_rag — 企业级混合检索系统
**路径**：[`hybrid_rag/`](./hybrid_rag/)

```
核心能力：
  ✅ BM25 + 向量双路检索融合（RRF 算法）
  ✅ 交叉编码器精排（Rerank）
  ✅ ChromaDB 向量存储
  ✅ FastAPI Web 服务封装
  ✅ 动态知识库更新

技术栈：ChromaDB · BM25 · Rerank · FastAPI
```

### 3. document_processor — 多格式文档解析器
**路径**：[`document_processor/`](./document_processor/)

```
核心能力：
  ✅ PDF / Word / Excel 多格式解析
  ✅ 结构化信息提取（表格、图表）
  ✅ 智能分块与元数据标注

技术栈：PyPDF · python-docx · openpyxl · LangChain Loaders
```

### 4. autogen_coder — 自动化代码 Agent
**路径**：[`autogen_coder/`](./autogen_coder/)

```
核心能力：
  ✅ AssistantAgent + CodeExecutorAgent 双 Agent 协作
  ✅ 本地沙箱代码执行
  ✅ 自动测试与修正循环

技术栈：AutoGen v0.4 · LocalCommandLineCodeExecutor
```

---

## 🗺️ 技术演进路线

```
Prompt 工程
    │
    ├──► Function Calling ──► MCP 协议
    │
    ├──► RAG 检索 ──► Embedding ──► 混合检索 hybrid_rag
    │         │
    │         └──► 多模态 RAG（图片/视频）
    │
    └──► LangGraph Agent
              │
              ├──► 深度记忆系统（摘要 + 长效画像）
              ├──► 多 Agent 协作
              ├──► HITL 人机协同 ──► RepoSense 实战
              └──► AutoGen 代码 Agent

Transformers 原理 ──► LoRA 微调 ──► 推理优化（KV Cache/vLLM）
                                          │
Ragas 评估 ──► LangSmith 追踪 ──────────► 生产部署
```

---

## ⚙️ 环境配置

```bash
# 核心依赖
pip install langchain langchain-openai langgraph
pip install openai chromadb faiss-cpu tiktoken
pip install mcp fastapi uvicorn sqlalchemy alembic
pip install ragas transformers pydantic

# 环境变量（参考 .env.example）
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=ls-...        # LangSmith 追踪
LANGCHAIN_TRACING_V2=true
```

---

## 📖 文档索引

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 项目入门指南 |
| [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) | 10 阶段学习精华汇总 |
| [GEMINI.md](./GEMINI.md) | AI 工程学习核心准则 |
| [agent_dev_guide.md](./agent_dev_guide.md) | Agent 开发完整指南 |
| [04-rag/ENTERPRISE_RAG_ARCHITECTURE.md](./04-rag/ENTERPRISE_RAG_ARCHITECTURE.md) | 企业 RAG 架构设计 |
| [15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md](./15-agent-architecture/ENTERPRISE_AGENT_WHITEPAPER.md) | Agent 架构白皮书 |
| [17-transformers-basics/SUMMARY.md](./17-transformers-basics/SUMMARY.md) | Transformer 技术摘要 |
| [09-evaluation/OBSERVABILITY_AND_EVALUATION.md](./09-evaluation/OBSERVABILITY_AND_EVALUATION.md) | 可观测性方案 |

---

> **架构师备注**：本项目已覆盖当前 AI 工程的全栈技术链路——从 Prompt 设计到 Agent 编排，从向量检索到模型微调，从单机实验到生产部署。建议按「模型交互基础 → 知识与记忆 → Agent 编排 → 评估上线」的顺序进行系统性学习，并以 **RepoSense** 和 **hybrid_rag** 作为阶段性验收项目。
