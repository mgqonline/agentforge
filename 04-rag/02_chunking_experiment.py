import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

def run_chunking_experiment():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "ai_learning_guide.txt")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # 初始化本地嵌入模型
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    # 定义三种不同的切分策略
    configs = [
        {"name": "极小块 (无重叠)", "size": 30, "overlap": 0},
        {"name": "极小块 (高重叠)", "size": 30, "overlap": 20},
        {"name": "标准块 (适中重叠)", "size": 200, "overlap": 50},
    ]

    query = "RAG 的组件有哪些？"
    print(f"用户提问: {query}\n")

    for config in configs:
        print(f"=== 实验方案: {config['name']} (Size={config['size']}, Overlap={config['overlap']}) ===")
        
        # 使用递归切分器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config['size'], 
            chunk_overlap=config['overlap']
        )
        texts = text_splitter.split_documents(documents)
        
        # 存入临时向量库 (内存)
        vectorstore = Chroma.from_documents(
            documents=texts, 
            embedding=embeddings,
        )
        
        # 检索最相关的 3 个片段以观察多样性
        docs = vectorstore.similarity_search(query, k=3)
        
        # 打印结果
        for i, doc in enumerate(docs):
            content = doc.page_content.replace("\n", "\\n")
            print(f"  片段 {i+1} [长度 {len(doc.page_content)}]: {content}")
        
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_chunking_experiment()
