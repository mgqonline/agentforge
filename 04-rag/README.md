<RAG 检索增强生成 · 深度学习与实战>
## 🎯 核心目标与应用场景
- 解决大语言模型（LLM）由于训练数据存在知识截止期限导致的信息滞后问题，以及面对垂直、私有领域知识时容易产生“幻觉”的业务痛点。
- **应用场景**：
  1. **企业内部知识库问答系统**：结合企业内部 wiki 和规章制度文档，提供精准的员工查询助手。
  2. **智能客服机器人**：基于产品手册和历史客诉数据，为客户提供准确快速的解决方案，降低人工客服成本。
  3. **专业文献研究助手**：处理长篇论文、研报或法律合同，从中快速定位关键条款及论点，辅助深度研究与分析。

## 🧠 技术原理与架构流程图
- RAG（Retrieval-Augmented Generation）技术通过“检索+生成”双管齐下。在模型生成回答之前，先根据用户的输入（Query）去向量数据库（或倒排索引）中搜索最相关的文档片段作为“上下文”（Context），随后大模型将用户输入和上下文拼接在一起，最终生成有依据、准确率高的回复。简单来说，就是给大模型配备了一个可以随时翻阅、快速定位的“外部参考资料库”，让它做到“开卷考试”。
- **架构流程图**：
```mermaid
graph TD
    %% 数据准备阶段
    subgraph Data Preparation [数据准备阶段 (离线)]
        A[私有文档] --> B(文档解析与清洗 Load)
        B --> C(文本切分 Chunking)
        C --> D(文本向量化 Embedding)
        D --> E[(向量数据库 Vector Store)]
    end
    
    %% 检索与生成阶段
    subgraph Query Process [检索与生成阶段 (在线)]
        F[用户提问 Query] --> G(提问向量化 Embedding)
        G --> H{混合检索 Hybrid Retrieval}
        E -.->|近似最近邻居 ANN| H
        H --> R(重排序 Rerank)
        R --> I(Context 上下文组装)
        F --> I
        I --> J(大语言模型 LLM Generation)
        J --> K[最终回答 Answer]
    end
```

## 🛠️ 操作方法与执行命令
# 1. 运行基础 RAG 流程，体验从文档加载到大模型回答的全过程
```bash
python 04-rag/01_basic_rag.py
```

# 2. 进行文本切分参数实验，对比不同 chunk_size 和 overlap 对检索质量的影响
```bash
python 04-rag/02_chunking_experiment.py
```

# 3. 运行 MMR (Maximal Marginal Relevance) 实验，测试检索结果的多样性，解决冗余内容问题
```bash
python 04-rag/03_mmr_experiment.py
```

# 4. 体验企业级混合检索架构（向量检索 + 关键字 BM25 检索）
```bash
python 04-rag/hybrid_retrieval_demo.py
```

# 5. 运行 Rerank (重排序) 流程，对初步检索结果进行二次精确打分与排序
```bash
python 04-rag/rerank_demo.py
```

## ⚠️ 注意事项与踩坑记录
- **向量模型依赖与网络**：由于演示代码通常依赖 `sentence-transformers` 等本地 Embedding 模型，初次运行时可能需要从 HuggingFace 自动下载模型。若处于国内网络环境极易超时，请提前配置代理，或使用国内镜像站：在终端执行 `export HF_ENDPOINT=https://hf-mirror.com`。
- **依赖库版本兼容性**：RAG 流程涉及 `langchain`、`chromadb`、`sentence-transformers` 和 `rank_bm25` 等多个第三方库。强烈建议锁定 requirements 中的版本号（尤其是 `langchain` 和 `chromadb` 经常发生破坏性 API 更新）。如遇导入失败或参数缺失报错，请第一时间检查包版本冲突。
- **Context 上下文长度限制**：检索出的多个召回片段合并后，总 Token 数一定不能超过 LLM 的最大上下文窗口限制。如遇相关报错需减小 `top_k` 召回数量，或接入支持更长上下文的大模型。
- **中文文本切分（Chunking）坑点**：直接使用 `RecursiveCharacterTextSplitter` 时，其默认是以英文标点为主。直接应用在中文上会导致切分效果极差，语义断裂严重。务必修改分隔符（separators），增加 `\n\n`、`。`、`！`、`？` 等中文标点字符，保证切分出的 Block 具备完整语义。
</RAG 检索增强生成 · 深度学习与实战>
