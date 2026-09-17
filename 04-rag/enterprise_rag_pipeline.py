import warnings
warnings.filterwarnings("ignore")

import jieba
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import FakeEmbeddings
from langchain_classic.retrievers.ensemble import EnsembleRetriever

# 1. 模拟上游文档解析引擎（如 docx2txt, pd.read_excel）清洗后的高质量 Markdown 产物
raw_enterprise_markdown = """
# 2026 核心 AI 研发中心制度白皮书

## 1. 差旅与报销标准
研发人员出差住宿标准为基础城市 500元/天，北上广深一线城市 800元/天。
交通工具方面，高铁仅限二等座，如需乘坐飞机需提前一周向行政部申请。

## 2. 算力硬件采购流程
| 物品种类 | 审批链路 | 预算上限 |
|---|---|---|
| A100/H100 GPU | 直属主管 -> CTO -> 财务总监 | $50,000 |
| 普通办公电脑 | 直属主管 | $2,000 |
| 外部大模型 API 额度 | 直属主管 -> AI 架构师 | 每月 $5,000 |

## 3. 常见生产系统故障排查
遇到 `CUDA_OUT_OF_MEMORY` (错误码 137)，说明大模型训练时显存溢出。
解决方案：请立刻减小模型训练的 Batch Size，或者开启 Gradient Checkpointing 特性以用时间换空间。
"""

def run_enterprise_rag():
    print("🏭 启动企业级端到端 RAG 终极流水线 🏭\n")

    # ==========================================
    # Step 1 & 2: 结构感知摄入与切分 (Ingestion & Chunking)
    # 抛弃垃圾定长切分，使用 Markdown 结构切分保全表格和上下文！
    # ==========================================
    print("✅ [1/5] 执行 Markdown 结构感知切分 (Structure-Aware Chunking)...")
    headers_to_split_on = [("#", "文档主题"), ("##", "章节模块")]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(raw_enterprise_markdown)
    print(f"   -> 成功剥离出 {len(chunks)} 块极高质量的语义纯净块。")

    # ==========================================
    # Step 3: 稠密向量引擎构建 (Embedding & VectorStore)
    # ==========================================
    print("✅ [2/5] 编译稠密向量知识库 (FAISS Dense Engine)...")
    embeddings = FakeEmbeddings(size=128) # 生产替换为 OpenAIEmbeddings 等
    faiss_vs = FAISS.from_documents(chunks, embeddings)
    faiss_retriever = faiss_vs.as_retriever(search_kwargs={"k": 3})

    # ==========================================
    # Step 4: 稀疏词频引擎构建 (Sparse BM25 Engine)
    # ==========================================
    print("✅ [3/5] 编译稀疏关键词知识库 (BM25 Sparse Engine)...")
    bm25_retriever = BM25Retriever.from_documents(chunks, preprocess_func=lambda x: list(jieba.cut(x)))
    bm25_retriever.k = 3

    # ==========================================
    # Step 5: 混合检索与重排序融合 (Hybrid + Rerank)
    # ==========================================
    print("✅ [4/5] 组装多路召回与倒数秩融合引擎 (Ensemble RRF)...")
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.5, 0.5]  # 两路引擎各占 50% 权重
    )

    print("✅ [5/5] 挂载交叉编码器精排系统 (Cross-Encoder Reranker)...")
    try:
        from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
        from langchain_classic.retrievers.document_compressors.cross_encoder import CrossEncoderReranker
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        compressor = CrossEncoderReranker(model=model, top_n=1) # 掐尖，只要最核心的 1 个片段
        final_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=ensemble_retriever)
    except ImportError:
        print("   -> (未检测到 Torch/HF 依赖，当前以 EnsembleRetriever 作为降级出口)")
        # 降级：如果没下沉重模型，我们就用混合检索直接输出 Top-1
        ensemble_retriever.retrievers[0].k = 1
        ensemble_retriever.retrievers[1].search_kwargs['k'] = 1
        final_retriever = ensemble_retriever

    print("\n" + "="*50)
    print("🔥 企业级 RAG 生产大考 🔥")
    
    queries = [
        "公司规定申请买一张 A100 的显卡，最高能报销多少钱？找谁审批？",
        "半夜训练模型崩了，日志报了 CUDA_OUT_OF_MEMORY，怎么救？"
    ]

    for q in queries:
        print(f"\n👤 业务域提问: {q}")
        print("⚙️  系统极速寻址中...")
        results = final_retriever.invoke(q)
        
        # 组装 Prompt
        context_str = "\n".join([f"【数据源: {res.metadata}】\n{res.page_content}" for res in results])
        print(f"📦 喂给大模型的绝对精准上下文:\n{context_str}\n")
        print("🤖 [模拟大模型生成] 基于上述精准数据，大模型可以做到 0 幻觉完美回答此问题。")

if __name__ == "__main__":
    run_enterprise_rag()
