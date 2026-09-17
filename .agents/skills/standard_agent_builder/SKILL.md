---
name: standard_agent_builder
description: 当用户要求“开发一个标准agent”、“新建一个AI助手”、“构建生产级agent”时自动触发此技能。用于指导AI生成具备高准确率（LangGraph反思循环、高阶RAG适配DeepSeek）的标准 Agent 骨架。
---

# 标准 Agent 开发规范 (Standard Agent Builder)

当用户要求你开发一个新的 Agent 时，你必须遵循以下生产级（95%准确率）设计规范。无论业务场景如何，请按照该标准生成代码：

## 1. 核心架构：LangGraph 状态机反思循环
永远不要只用一个简单的 LLM API（`ChatOpenAI().invoke()`）包装成 Agent 交差。必须使用 **LangGraph** 构建带“反思与修正”的循环工作流 (StateGraph)。
核心节点必须包含：
- `generate`: 生成初稿。
- `evaluate`: 审查草稿质量（是否产生幻觉、是否解答了问题）。
- `conditional_edge`: 如果审查不通过，打回 `generate` 重写。

## 2. 默认模型配置 (适配用户的环境)
考虑到用户本地的 `.env` 环境，默认的 LLM 必须且强制配置为使用 DeepSeek 代理：
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model="deepseek-chat", 
    base_url="https://api.deepseek.com/v1",
    temperature=0
)
```

## 3. 高级 RAG 最佳实践
如果该 Agent 需要接入知识库和进行文档检索：
- **禁止**使用简单的单次向量召回。
- 考虑到 DeepSeek API 目前不支持 Embeddings 接口，建议在测试时引入 `langchain_community.embeddings.DeterministicFakeEmbedding` 占位，或引导用户配置本地免费的 HuggingFace 嵌入。
- 必须引入重排过滤机制：使用 `LLMChainExtractor` 配合 DeepSeek 进行上下文的动态筛选压缩。

## 4. 你的行动指南
在触发此技能后，作为 AI，请你：
1. 询问用户这个新建 Agent 的**具体业务场景**（比如：它需要什么外部工具？需要接入什么样的特定知识库？）。
2. 在用户确认场景后，参考附带的 `examples/template_agent.py`（如果有），立刻为用户生成一套定制化的、包含 LangGraph 完整逻辑流的代码。
