import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

def run_mmr_experiment():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "ai_learning_guide.txt")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # 1. 初始化本地嵌入模型
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    # 2. 使用较大的重叠度切分，模拟冗余场景
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=80)
    texts = text_splitter.split_documents(documents)
    
    # 3. 建立向量库
    vectorstore = Chroma.from_documents(documents=texts, embedding=embeddings)

    query = "RAG 的核心组件有哪些？"
    print(f"用户提问: {query}\n")

    # 方案 A: 普通相似度检索 (Similarity Search)
    print("=== 方案 A: 普通相似度检索 (Top 3) ===")
    docs_sim = vectorstore.similarity_search(query, k=3)
    for i, doc in enumerate(docs_sim):
        content = doc.page_content.replace('\n', ' ')
        print(f"  片段 {i+1}: {content}")

    print("\n" + "-"*50 + "\n")

    # 方案 B: MMR 检索 (Maximal Marginal Relevance)
    # fetch_k: 先筛选出前 20 个相关的
    # k: 从这 20 个里选出 3 个最不重合的
    print("=== 方案 B: MMR 检索 (Top 3, fetch_k=20) ===")
    docs_mmr = vectorstore.max_marginal_relevance_search(query, k=3, fetch_k=20)
    for i, doc in enumerate(docs_mmr):
        content = doc.page_content.replace('\n', ' ')
        print(f"  片段 {i+1}: {content}")

if __name__ == "__main__":
    run_mmr_experiment()
