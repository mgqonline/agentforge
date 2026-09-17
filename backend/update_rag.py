import re

with open("rag_engine.py", "r") as f:
    content = f.read()

# Fix the EnsembleRetriever weights in the load branch
content = re.sub(
    r"weights=\[0\.3, 0\.7\]",
    "weights=[0.9, 0.1]",
    content
)
# Ensure the retrievers order in the load branch matches the new weights
content = re.sub(
    r"retrievers=\[self\.bm25_retriever, self\.chroma_retriever\],",
    "retrievers=[self.bm25_retriever, self.chroma_retriever],",
    content
) # Actually, if bm25 is first, 0.9 goes to bm25. Let's make sure.

# Fix the build branch to save bm25.pickle
save_bm25_code = """
        # Initialize Dense Retriever (Chroma)
        if os.path.exists(self.persist_dir) and os.listdir(self.persist_dir):
            print("[RAG] 加载现有的本地知识库 (ChromaDB)...")
            vectorstore = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
        else:
            print("[RAG] 创建新的本地知识库 (ChromaDB)...")
            vectorstore = Chroma.from_documents(documents, self.embeddings, persist_directory=self.persist_dir)
            
        self.chroma_retriever = vectorstore.as_retriever()
        
        # 保存 BM25 索引到硬盘，防止下次重启时找不到
        import pickle
        bm25_path = os.path.join(self.persist_dir, 'bm25.pickle')
        with open(bm25_path, 'wb') as f:
            pickle.dump(self.bm25_retriever, f)
"""
content = re.sub(
    r"# Initialize Dense Retriever \(Chroma\).*?self\.chroma_retriever = vectorstore\.as_retriever\(\)",
    save_bm25_code.strip(),
    content,
    flags=re.DOTALL
)

with open("rag_engine.py", "w") as f:
    f.write(content)

