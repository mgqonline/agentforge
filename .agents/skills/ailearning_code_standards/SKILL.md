---
name: ailearning_code_standards
description: 当你在 ailearning 项目中进行任何代码开发、重构或架构设计时，必须自动触发此技能。包含项目的 Python 规范、框架约定及 AI 代码治理准则。
---

# AILearning 项目开发与代码规范指南

你在 `ailearning` 项目中作为资深 AI 工程师进行代码生成、重构或项目维护时，必须严格遵守以下准则与架构约定。

## 1. 核心研发准则
- **实践驱动**：只提供能真实运行的代码，杜绝无法跑通的“伪代码”。所有技术方案必须能在本地闭环验证。
- **文档先行**：每次引入新架构或踩坑后，必须同步更新配套的 Markdown 文档。
- **模块化设计**：拒绝意大利面条式代码，确保职责单一（例如：检索引擎与 FastAPI 路由必须完全解耦）。

## 2. 环境与依赖约束
- **Python 版本**：当前项目基准为 `Python 3.11`。
- **虚拟环境**：所有的 pip 安装和脚本执行，必须在项目根目录或当前工作目录激活 `venv` 后进行（执行 `source venv/bin/activate` 或 `source ../venv/bin/activate`）。
- **库版本对齐**：
  - FastAPI 构建异步后端
  - LangChain / LangGraph 作为核心 Agent 框架
  - Pydantic v2 用于数据校验与结构化输出
  - 核心大模型接口优先对接 DeepSeek (兼容 OpenAI SDK)

## 3. 代码风格与质量红线
- **强类型推导 (Type Hints)**：所有的函数、类方法必须带有完整的参数类型与返回类型注解（如 `def ask(self, query: str) -> str:`）。
- **异常捕获与日志 (Error Handling & Logging)**：
  - 严禁使用空白的 `except Exception: pass`。
  - 所有网络请求（如 LLM 调用、向量检索）必须包含完整的 try-catch，并输出清晰的报错上下文。
- **边界与“Happy Path”防范**：AI 编码容易忽略极端情况。必须在代码中处理如：检索结果为空、外部 API 超时、用户输入空字符串等场景。

## 4. 框架使用约定 (Hybrid RAG & LangChain)
- **流式输出**：涉及到用户问答的接口，必须使用 FastAPI 的 `StreamingResponse` 结合 Python 的 `yield` 生成器，实现打字机效果。注意流式返回的 JSON 必须设定 `ensure_ascii=False`。
- **结构化输出**：如果大模型无法原生支持 `.with_structured_output()`，必须回退到 `PydanticOutputParser` + JSON 约束的可靠方案。
- **提示词工程**：将庞大的 Prompt 模板独立抽离，不要硬编码在复杂的业务逻辑函数中。

## 5. AI 代码治理与安全约束
- **绝对红线**：禁止将真实的线上数据库密码、云服务 Secret Key 硬编码在代码中。必须使用 `.env` 与 `os.getenv()` 管理配置。
- **前端网络路径规范**：前端网络请求必须使用相对路径（如 `/api/v1/...`），严禁硬编码 `http://localhost:6001` 等绝对端口，以保证容器化反代与多端部署无缝运行。
- **沙箱安全与防逃逸**：修改执行器相关代码时，必须遵守 `sandbox_security_guard` 规范，所有执行代码必须通过 AST 静态审查与资源配额约束。
- **幻觉排查**：引入第三方库函数前，必须确认该函数在当前版本真实存在（如警惕 LangChain 频繁变动的 API 废弃）。
- **过度设计防范**：不需要为了炫技引入复杂的元类 (Metaclass) 或生僻的设计模式。代码应以“团队其他初级开发者能轻松看懂并维护”为最高标准。

> **执行要求**：在生成任何代码前，请先在思考阶段回顾本 SKILL，并确保你的输出 100% 契合上述要求。
