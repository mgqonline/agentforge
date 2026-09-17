import warnings
warnings.filterwarnings("ignore")

import jieba
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import FakeEmbeddings
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langchain_core.documents import Document

# ==========================================
# 模拟企业内部的知识库语料
# 一些文档更适合“语义检索”，另一些(如代码日志、专有名词)更适合“关键词检索”
# ==========================================
docs = [
    Document(page_content="苹果公司（Apple Inc.）在加州发布了最新的 iPhone 16，具备强大的大模型 AI 能力。", metadata={"id": 1}),
    Document(page_content="今天下班去水果超市，发现富士苹果和香蕉搞特价，都很便宜。", metadata={"id": 2}),
    Document(page_content="【生产故障】系统报错: Exception in thread 'main' java.lang.NullPointerException at com.example.MyClass.java:18", metadata={"id": 3}),
    Document(page_content="【开发文档】如何解决 Java 空指针异常？通常需要检查对象是否被正确初始化，或者加上判空逻辑。", metadata={"id": 4}),
]

def hybrid_search_demo():
    print("🚀 正在构建混合检索 (Hybrid Retrieval) 引擎...\n")

    # --------------------------------------------------
    # 1. 初始化稀疏检索器 (BM25 - 关键词匹配的绝对王者)
    # 特别擅长：包含人名、地名、长串报错代码(如 NullPointerException)的绝对匹配。
    # 致命弱点：不懂同义词，搜“土豆”绝对搜不到“马铃薯”。
    # --------------------------------------------------
    def chinese_tokenizer(text):
        # 针对中文语料，使用结巴分词代替默认的英文空格分词
        return list(jieba.cut(text))
        
    bm25_retriever = BM25Retriever.from_documents(docs, preprocess_func=chinese_tokenizer)
    bm25_retriever.k = 2  # 只返回前 2 条

    # --------------------------------------------------
    # 2. 初始化稠密检索器 (FAISS 向量检索 - 语义理解的王者)
    # 特别擅长：同义词映射、口语化表达、总结性提问 (如搜“买点吃的东西”能搜到“超市特价”)
    # 致命弱点：对唯一的 UUID、具体的专有名词和代码大小写极度不敏感。
    # --------------------------------------------------
    embeddings = FakeEmbeddings(size=128) # 测试用模拟模型。生产请换为 OpenAIEmbeddings 等真实模型
    faiss_vectorstore = FAISS.from_documents(docs, embeddings)
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 2})

    # --------------------------------------------------
    # 3. 终极融合：组装 RRF 混合检索器 (Ensemble Retriever)
    # 采用 RRF (Reciprocal Rank Fusion - 倒数秩融合) 算法对两者的结果重新打分并合并排序
    # --------------------------------------------------
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.5, 0.5] # 两者各占一半权重。你可以根据业务(代码多还是文章多)自行偏压
    )

    # ==================== 测试环节 ====================

    query1 = "我要买点吃的水果"
    print(f"❓ 测试 1 (偏语义提问): '{query1}'")
    print("🔍 [混合检索] 返回结果:")
    # 底层会自动让 BM25 和 FAISS 分别去查，然后再合并排名
    results1 = ensemble_retriever.invoke(query1)
    for i, res in enumerate(results1):
        print(f"   [{i+1}] {res.page_content}")
        
    print("-" * 50)

    query2 = "系统报了 NullPointerException 怎么排查？"
    print(f"❓ 测试 2 (包含专有名词/代码的提问): '{query2}'")
    print("🔍 [混合检索] 返回结果:")
    results2 = ensemble_retriever.invoke(query2)
    for i, res in enumerate(results2):
        print(f"   [{i+1}] {res.page_content}")

if __name__ == "__main__":
    hybrid_search_demo()
