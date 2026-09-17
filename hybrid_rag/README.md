# Hybrid RAG 检索系统

**生产级混合检索 RAG 系统**，整合三种核心技术打造高精准知识问答平台。

## 系统架构

```
用户问题
   │
   ├──► BM25 关键字检索 ──────────────┐
   │    (rank_bm25 + jieba分词)       │
   │                                  ▼
   └──► ANN 向量语义检索 ───► RRF 融合排序 ──► CrossEncoder 重排序 ──► DeepSeek 生成答案
        (ChromaDB + sentence-         │
         transformers)                │
                                      ▼
                               可视化 Web 界面
```

## 技术组件

| 组件 | 技术选型 | 作用 |
|------|---------|------|
| 关键字检索 | `rank_bm25` + `jieba` | 精确词汇匹配，不漏热门关键词 |
| 向量检索 | `ChromaDB` + `paraphrase-multilingual-MiniLM` | 语义理解，跨语言召回 |
| 融合算法 | RRF (倒数排名融合) | 取两路检索优势，合并去重 |
| 重排序 | `cross-encoder/ms-marco-MiniLM-L-6-v2` | 精细打分，显著提升 Top-K 精度 |
| LLM 生成 | DeepSeek Chat API | 基于检索上下文生成最终答案 |
| Web UI | 纯 HTML + CSS + JS | 四列可视化对比，实时流水线动画 |
| 后端 | FastAPI + Uvicorn | RESTful API，支持热重载 |

## 快速启动

### 1. 确保已激活虚拟环境并安装依赖

```bash
source agent_env/bin/activate
pip install -r hybrid_rag/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. 配置 API Key（用于 RAG 生成答案）

在项目根目录 `.env` 文件中确保有：
```
DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 启动服务

```bash
# 方式一：一键脚本
bash hybrid_rag/start.sh

# 方式二：手动启动
cd hybrid_rag
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 打开浏览器

- **Web UI（测试界面）**：http://localhost:8000
- **API 文档（Swagger）**：http://localhost:8000/docs

## API 接口说明

### 混合检索（只检索，不生成答案）
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "BM25算法原理", "top_k": 5}'
```

### RAG 问答（检索 + LLM 生成答案）
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是混合检索？"}'
```

### 添加文档到知识库
```bash
curl -X POST http://localhost:8000/api/documents/add \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"content": "你的文档内容...", "metadata": {"category": "分类"}}
    ]
  }'
```

## Web 界面功能

- **四列对比视图**：BM25 / 向量检索 / RRF融合 / 重排序结果并排显示
- **分数可视化**：每条结果显示相关性分数条
- **流水线进度动画**：实时展示检索各阶段状态
- **AI 综合答案**：点击 RAG 问答按钮获取 AI 基于知识库的回答
- **快速测试用例**：内置 6 个测试问题，一键填入搜索框
- **知识库管理**：在界面上直接添加/清空文档

## 文件结构

```
hybrid_rag/
├── app.py           # FastAPI 后端服务
├── rag_engine.py    # 核心检索引擎（BM25 + ChromaDB + Reranker）
├── sample_data.py   # 示例知识库（18条AI领域中文文档）
├── requirements.txt # Python 依赖
├── start.sh         # 一键启动脚本
├── chroma_db/       # ChromaDB 向量索引（运行后自动生成）
└── static/
    └── index.html   # Web 测试界面
```

## 踩坑记录

> 记录实验过程中遇到的问题，持续更新...
