# 24-backend · 纯异步企业级 Agent 后端与知识检索

## 🎯 核心目标与应用场景
为企业级知识库 (RAG) 打造一个**零阻塞、高并发、强鲁棒性**的核心驱动中枢。彻底解决大模型在长序列思考时的 HTTP 超时问题，并通过降维打击（BM25）规避国内企业内网复杂的 SSL/DPI 防火墙阻断。

**应用场景**：
1. **企业内网 AI 门户中枢**：作为全公司统一的 AI 网关，支撑成百上千员工并发连接提问。
2. **多模态流式响应基座**：不仅能处理纯文本，还能流式处理高清图片的解析（Vision）请求，提供类似于 ChatGPT 的打字机下发体验。
3. **专家级 Agent 工作流引擎**：支持动态下发各种内部状态（如“正在查阅图纸”、“正在分析报表”），不再是死板的一问一答。

---

## 🧠 技术原理与架构流程图

### 1. 核心技术架构介绍
本后端完全抛弃了传统的 Flask + 同步 HTTP 架构，采用了最激进但也最适合大模型的全异步流式架构：
*   **网关接入层：FastAPI + WebSockets**。全双工长连接管道，服务器可以随时向前端主动推流（状态信息或 Token），客户端再也无需轮询，极大降低了服务器的握手开销。
*   **通信核心层：OpenAI AsyncClient 原生库**。刻意绕过了臃肿的 Langchain LLM 封装，直接使用原生底层库，彻底规避了 `transformers` 触发的 Python 底层 `importlib` 包扫描 Bug。
*   **知识检索层：BM25 稀疏检索架构**。抛弃了高度依赖外网下载、极易遭遇 SSL 阻断的神经网络 Embedding（如 Chroma），采用基于 TF-IDF 算法演进的经典倒排索引。

### 2. 采用此技术方案的极大好处
1. **免疫网络封锁**：完全拔掉对 HuggingFace 权重的依赖，BM25 分词全部在本地内存瞬间完成，即使在完全断网的保密机房也能极速捞取文档。
2. **零延时流转感知**：WebSocket 允许后端在模型思考期间（如“专家模式”）向前端疯狂抛出中间态日志（`{"type": "status"}`），填补了用户的等待焦虑。
3. **极简运维**：没有臃肿的向量数据库中间件（如 Qdrant/Milvus），一个 `.pkl` 文件搞定全部知识图谱。

```mermaid
graph TD;
    A[前端 WebSocket 客户端] -->|长连接 JSON (包含图片)| B(FastAPI WebSocket 端点)
    
    subgraph 本地检索沙箱
        B -->|1. 提取 Query| C[BM25 Retriever 引擎]
        C -->|基于词频倒排索引| D[(本地 .md 文件集)]
        D -->|返回高相关 Chunk| C
    end
    
    subgraph 异步流式引擎
        B -->|2. 拼装 多模态提示词| E[OpenAI AsyncClient]
        E -->|异步长连接| F(远端 DeepSeek/GPT4o)
        F -->|Yield 流式 Token| E
    end
    
    E -.->|3. WebSocket Send| A
    C -.->|推送中间状态| A
    
    style B fill:#f99,stroke:#333,stroke-width:2px
    style C fill:#9f9,stroke:#333,stroke-width:2px
    style E fill:#9f9,stroke:#333,stroke-width:2px
```

---

## 🛠️ 操作方法与执行命令 (二次开发方法)

**1. 启动后端服务**
```bash
cd backend
# 必须先激活虚拟环境
python main.py
```

**2. 二次开发指南**
*   **挂载全新的知识库**：只需将你们业务产生的 Markdown（或 TXT）直接扔进 `rag_engine.py` 所扫描的 `data_dir`（目前默认扫描项目根目录），然后删除 `bm25_retriever.pkl`。下次重启服务时，它会自动为你重新构建全新的本地检索词典。
*   **定制专家模式 (Agent Workflow)**：在 `main.py` 的 `if mode == "expert":` 分支下，你可以接入 LangGraph 或 CrewAI。在节点流转时，只需调用 `await websocket.send_json({"type": "status", "content": "..."})` 就能让前端实时看到你的多智能体正在干什么。
*   **替换底层大模型**：修改 `.env` 里的 `OPENAI_API_BASE`。因为我们使用了最标准的 OpenAI AsyncClient，它完美兼容包括 DeepSeek、Qwen、Ollama 在内的市面上 99% 的模型，无需改动任何核心代码。

---

## ⚠️ 注意事项与踩坑记录

- **Python 3.11 隐形炸弹**：我们在开发初期曾使用 `langchain_openai`，结果其底层的 `transformers` 触发了 `sys.intern() must be str, not None` 致命异常。二次开发时请**务必坚持使用原生的 `openai` 库**发起请求，不要引入不必要的高层封装套件。
- **WebSocket 资源泄漏**：`main.py` 中已经使用了严格的 `while True` 配合 `except WebSocketDisconnect:`。如果你在循环体内引入了数据库游标或外部 HTTP 会话，**必须**在 `finally` 或 `except` 块中进行释放，否则断开重连会导致严重的文件句柄泄露。
- **图片尺寸告警**：当前端传入的 Base64 字符串过大（例如 20MB 的原图）时，可能会触发 FastAPI 默认的 Websocket Payload 上限，引发连接直接断开 (1006 异常)。生产环境中如果涉及 4K 图片传输，建议在前端加入 Canvas 压缩，或者修改 Uvicorn 的 `ws-max-size`。
