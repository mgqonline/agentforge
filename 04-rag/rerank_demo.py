import warnings
warnings.filterwarnings("ignore")

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

import jieba

# ==========================================
# 模拟知识库语料
# ==========================================
docs = [
    Document(page_content="苹果手机（iPhone）的电池续航一般是一整天。", metadata={"id": 1}),
    Document(page_content="今天中午吃什么？吃个苹果怎么样？", metadata={"id": 2}),
    Document(page_content="【核心维修指南】如何更换 iPhone 14 的电池？首先你需要购买一块官方电池并准备十字螺丝刀，然后用吹风机加热边缘...", metadata={"id": 3}),
    Document(page_content="苹果树在春天开花，秋天结果。", metadata={"id": 4}),
    Document(page_content="我的手机没电了，需要充电宝。", metadata={"id": 5}),
]

def demo_rerank():
    print("🚀 启动两阶段检索架构 (Two-Stage Retrieval) 演示\n")
    query = "我要怎么给我的苹果手机换电池？"
    print(f"👤 用户提问: '{query}'\n")

    # ==========================================
    # 阶段一：初筛召回 (Recall / 粗排)
    # 使用轻量级检索器（如 BM25 或 FAISS）快速从百万文档中捞出 Top-5
    # ==========================================
    print("=== 第一阶段：粗排召回 (Fast Recall) ===")
    base_retriever = BM25Retriever.from_documents(docs, preprocess_func=lambda text: list(jieba.cut(text)))
    base_retriever.k = 5  # 把相关的沾边的全捞出来
    
    base_results = base_retriever.invoke(query)
    print("🔍 未经 Rerank 的 Top-5 结果（注意排名顺序）：")
    for i, res in enumerate(base_results):
        # 你会发现，有时候由于词频计算，无关的短句子反而排在前面
        print(f"   [{i+1}] {res.page_content[:40]}...")

    # ==========================================
    # 阶段二：重排序 (Rerank / 精排)
    # 引入重不可攀的 CrossEncoder 交叉注意力模型，对刚刚捞出的 5 条重新进行逐字打分
    # ==========================================
    print("\n=== 第二阶段：精准重排 (Rerank) ===")
    print("⏳ 正在唤醒交叉编码器 (CrossEncoder) 进行深度语义推理打分...")
    
    try:
        from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
        from langchain.retrievers.document_compressors import CrossEncoderReranker
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        # 生产环境中强烈推荐智源研究院的：BAAI/bge-reranker-v2-m3
        # 这里为了演示不卡顿，使用一个极小的英文轻量模型（如果本地没下过模型，大概需下载80MB）
        model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        # 将 top_n 设为 2：只要最精华的前 2 条发给大模型生成答案
        compressor = CrossEncoderReranker(model=model, top_n=2)
        
        # 组装完整的流线：ContextualCompressionRetriever 会自动先调基础检索，再调 Rerank
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever
        )
        
        reranked_results = compression_retriever.invoke(query)
        print("\n🎯 Rerank 后的 Top-2 结果 (彻底纠正了排名)：")
        for i, res in enumerate(reranked_results):
            print(f"   [{i+1}] {res.page_content}")
            
    except ImportError:
        print("\n⚠️ 缺失 sentence-transformers 等重型深度学习依赖，触发模拟 Rerank 展示...")
        print("🎯 Rerank 后的 Top-2 结果 (模拟交叉打分后，真正解决问题的文档被提到了第一位)：")
        print(f"   [1] {docs[2].page_content}")
        print(f"   [2] {docs[0].page_content}")

if __name__ == "__main__":
    demo_rerank()
