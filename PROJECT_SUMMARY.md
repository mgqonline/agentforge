# AI 工程化实战路线：从入门到生产级 Agent

本文件汇总了本项目全二十三个阶段的学习精华，记录了从基础指令到复杂智能体编排，再到企业级架构部署的完整路径。

---

## 🚀 路线图概览

### 1. [Prompt 工程](./01-prompt-engineering/)
- **重点**: 系统提示词、思维链 (CoT)、少样本学习 (Few-shot)。
- **原理**: 利用 In-context Learning 引导模型推理。

### 2. [Function Calling](./02-function-calling/)
- **重点**: 工具定义与模型绑定。
- **原理**: 模型输出结构化 JSON 请求，外部环境执行动作。

### 3. [MCP 协议](./03-mcp/)
- **重点**: 标准化 AI 与数据源连接 (Model Context Protocol)。
- **原理**: 实现 Server/Client 架构，统一工具调用标准。

### 4. [RAG 检索增强生成](./04-rag/)
- **重点**: 文本切分、向量存储 (Chroma)、MMR 检索策略。
- **原理**: 为 LLM 挂载“外挂知识库”，减少幻觉，提升时效性。

### 5. [Embedding 深度理解](./05-embedding/)
- **重点**: 余弦相似度、向量空间、逻辑否定识别。
- **原理**: 文本的数学映射，揭示语义相关性与逻辑一致性的差异。

### 6. [Agent 基础 (LangGraph)](./06-agent-basics/)
- **重点**: 状态图 (StateGraph)、节点与边。
- **原理**: 将 Agent 构建为有状态的状态机，使循环逻辑可控。

### 7. [Agent 深度记忆](./07-advanced-memory/)
- **重点**: 摘要记忆 (Summary)、长效用户画像。
- **原理**: 模拟人类瞬时记忆与长期记忆的分工，优化上下文窗口。

### 8. [多模态 RAG](./08-multimodal/)
- **重点**: 图片描述 (Captioning)、联合嵌入 (CLIP)、视频时序检索。
- **原理**: 全媒介信息向量化，实现“看图/看视频”检索。

### 9. [评估与可观测性](./09-evaluation/)
- **重点**: RAGAS 评估框架（打分模型）。
- **原理**: 科学量化 RAG 质量，定位系统瓶颈（搜不到 vs 瞎编）。

### 10. [端到端生产级实战](./projects/repo_sense/)
- **重点**: 人机协同审批 (HITL)、断点续传。
- **原理**: 在高风险操作前引入人类决策，确保 Agent 的可控性与安全性。

### 11. [Python 进阶](./11-python-advanced/)
- **重点**: 装饰器、生成器、异步 IO、元类。
- **原理**: 夯实基础编程范式，为编写高性能复杂 AI 系统打底。

### 12. [FastAPI 进阶](./12-fastapi-advanced/)
- **重点**: 异步路由、依赖注入、后台任务、中间件。
- **原理**: 构建高并发的 AI 接口层。

### 13. [SQLAlchemy ORM](./13-sqlalchemy-advanced/)
- **重点**: 关系映射、长事务管理、Alembic 数据迁移。
- **原理**: 结构化数据的安全高效持久化。

### 14. [Celery 异步任务](./14-celery-advanced/)
- **重点**: 分布式任务队列、定时调度。
- **原理**: 将耗时大模型调用从主线程剥离，实现高可用。

### 15. [企业级 Agent 架构设计](./15-agent-architecture/)
- **重点**: 安全边界、细粒度权限控制、可观测性设计。
- **原理**: 将 Agent 从玩具级提升至工业级可用标准。

### 16. [人脸识别](./16-face-recognition/)
- **重点**: InsightFace、ONNX 部署、活体检测。
- **原理**: 边缘侧及轻量级视觉模型的推理与集成。

### 17. [Transformer 原理与优化](./17-transformers-basics/)
- **重点**: Tokenizer 机制、Attention 注意力、LoRA 微调、KV Cache。
- **原理**: 深入大模型底层逻辑，理解显存占用和推理加速的核心。

### 18. [高性能推理与部署架构](./18-inference-serving/)
- **重点**: vLLM、TensorRT-LLM、Triton Inference Server、量化 (INT8/AWQ)。
- **原理**: 实现企业级吞吐量的低延迟、高并发大模型部署引擎。

### 19. [大模型微调实战](./19-model-finetuning/)
- **重点**: SFT（指令微调）、RLHF/DPO（人类偏好对齐）、Unsloth 框架实操。
- **原理**: 注入专属垂直领域知识，打造企业专属领域模型。

### 20. [知识引擎与高阶 RAG](./20-graph-rag/)
- **重点**: GraphRAG、复杂表格多模态抽取、Agentic RAG。
- **原理**: 引入图结构数据表达复杂实体关系，实现多跳逻辑推理和长线分析。

### 21. [复杂多智能体协同](./21-multi-agent-scale/)
- **重点**: CrewAI/MetaGPT、Swarm 分层架构、代码 Agent 安全沙箱机制 (E2B)。
- **原理**: 面向企业复杂工作流的群体智能编排，自动纠错与大规模协同。

### 22. [AI 安全与红蓝对抗](./22-ai-security/)
- **重点**: 提示词注入攻击与防御 (Prompt Injection)、越狱对抗测试、细粒度 RBAC 鉴权。
- **原理**: 守住 Agent 执行的最后一道安全防线，确保敏感操作不出错。

### 23. [端侧与异构计算](./23-edge-ai/)
- **重点**: MLX 框架、ONNX 模型端侧运行、CoreML。
- **原理**: 在 Apple Silicon 等边缘侧设备上实现超低延迟的本地化私密部署。

---

## 🏆 核心实战成果：RepoSense 代码助手
本项目最终孵化了 **RepoSense** (位于 `projects/repo_sense/`)。
它集成了代码索引、状态机决策、多文件修改及 **HITL 审批机制**，是一个可以直接应用于本地开发的工程级助手原型。

## 🛠️ 环境要求
- Python 3.10+
- 向量数据库: Chroma
- 核心框架: LangChain, LangGraph, Ragas
- 模型协议: MCP (Model Context Protocol)
