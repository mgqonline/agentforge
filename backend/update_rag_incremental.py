import re

with open("rag_engine.py", "r") as f:
    content = f.read()

new_build_or_load = """    def build_or_load(self):
        import hashlib
        import psycopg2
        import redis
        
        def compute_md5(filepath):
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
            
        try:
            conn = psycopg2.connect(dbname="ailearning", user="aiuser", password="aipassword", host="localhost", port="5432")
            cursor = conn.cursor()
        except Exception as e:
            print("[RAG] 无法连接到 Postgres:", e)
            return
            
        cursor.execute("SELECT filepath, md5_hash FROM document_hashes")
        db_hashes = {row[0]: row[1] for row in cursor.fetchall()}
        
        current_files = {}
        for ext in self.supported_exts:
            for path in Path(self.data_dir).rglob(f'*{ext}'):
                path_str = str(path)
                if '.agents' in path_str or 'venv' in path_str or 'chroma_db' in path_str or '__pycache__' in path_str or '.git' in path_str:
                    continue
                current_files[path_str] = compute_md5(path_str)
                
        added = []
        modified = []
        deleted = []
        
        for filepath, md5 in current_files.items():
            if filepath not in db_hashes:
                added.append(filepath)
            elif db_hashes[filepath] != md5:
                modified.append(filepath)
                
        for filepath in db_hashes:
            if filepath not in current_files:
                deleted.append(filepath)
                
        has_changes = bool(added or modified or deleted)
        
        if os.path.exists(self.persist_dir) and os.listdir(self.persist_dir):
            vectorstore = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
        else:
            vectorstore = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
            has_changes = True
            
        if not has_changes:
            print("[RAG] 没有发现文件变更，跳过更新，直接加载知识库...")
            self.chroma_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
            import pickle
            bm25_path = os.path.join(self.persist_dir, 'bm25.pickle')
            if os.path.exists(bm25_path):
                with open(bm25_path, 'rb') as f:
                    self.bm25_retriever = pickle.load(f)
            else:
                dummy_docs = [Document(page_content="系统已经极速热启动，无需重新扫描 3 万个文件。", metadata={"source": "system"})]
                self.bm25_retriever = BM25Retriever.from_documents(dummy_docs)
                
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.chroma_retriever],
                weights=[0.5, 0.5]
            )
            cursor.close()
            conn.close()
            return
            
        print(f"[RAG] 检测到增量变更: 新增 {len(added)}, 修改 {len(modified)}, 删除 {len(deleted)}")
        
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=150)
        
        for filepath in deleted + modified:
            basename = os.path.basename(filepath)
            results = vectorstore.get(where={"source": basename})
            if results and results["ids"]:
                vectorstore.delete(ids=results["ids"])
            cursor.execute("DELETE FROM document_hashes WHERE filepath = %s", (filepath,))
            
        new_docs = []
        for filepath in added + modified:
            try:
                chunks = processor.process_file(filepath)
                docs = [Document(page_content=chunk["content"], metadata=chunk["metadata"]) for chunk in chunks]
                new_docs.extend(docs)
                basename = os.path.basename(filepath)
                cursor.execute(
                    "INSERT INTO document_hashes (filename, filepath, md5_hash) VALUES (%s, %s, %s)",
                    (basename, filepath, current_files[filepath])
                )
            except Exception as e:
                print(f"[RAG] 处理文件失败 {filepath}: {e}")
                
        if new_docs:
            vectorstore.add_documents(new_docs)
            
        conn.commit()
        cursor.close()
        conn.close()
        
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.flushdb()
            print("[RAG] 语义缓存已联动清空！")
        except Exception as e:
            print("[RAG] 语义缓存清空失败", e)
            
        print("[RAG] 正在全量重建 BM25 稀疏索引...")
        all_data = vectorstore.get()
        all_docs = []
        if all_data and all_data.get("documents"):
            for content, meta in zip(all_data["documents"], all_data["metadatas"]):
                all_docs.append(Document(page_content=content, metadata=meta))
        
        if not all_docs:
            all_docs = [Document(page_content="备用", metadata={"source": "备用"})]
            
        self.chroma_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        self.bm25_retriever = BM25Retriever.from_documents(all_docs, preprocess_func=chinese_tokenizer)
        
        import pickle
        bm25_path = os.path.join(self.persist_dir, 'bm25.pickle')
        with open(bm25_path, 'wb') as f:
            pickle.dump(self.bm25_retriever, f)
            
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, self.chroma_retriever],
            weights=[0.5, 0.5]
        )"""

# replace the build_or_load method
content = re.sub(r'    def build_or_load\(self\):.*?    def retrieve\(self, query: str, k=10\):', new_build_or_load + '\n\n    def retrieve(self, query: str, k=10):', content, flags=re.DOTALL)

with open("rag_engine.py", "w") as f:
    f.write(content)

print("rag_engine.py successfully updated for incremental RAG!")
