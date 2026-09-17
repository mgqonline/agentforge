import os
import sys
import jieba
from pathlib import Path

# 添加 project root 到 sys.path，以便能引用 document_processor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from document_processor.doc_parser import DocumentProcessor

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from modelscope import snapshot_download
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langsmith import traceable
from rag_security import rag_guard
from dfl_engine import dfl_fusion

def chinese_tokenizer(text):
    return list(jieba.cut(text))

class RAGEngine:
    def __init__(self, data_dir="../document_processor/samples"):
        self.data_dir = data_dir
        self.persist_dir = os.path.join(os.path.dirname(__file__), 'chroma_db')
        self._embeddings = None
        self._model_dir = None
        self.ensemble_retriever = None
        # 支持通过 document_processor 解析的所有格式
        self.supported_exts = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md', '.csv', '.json', '.pptx', '.html', '.htm', '.xml'}

    @property
    def embeddings(self):
        """懒加载模型权重，避免服务启动阻塞和健康检查超时"""
        if self._embeddings is None:
            # 优先查找本地持久化挂载目录 models
            local_model_path = os.path.join(os.path.dirname(__file__), "models", "bge-m3")
            if os.path.exists(local_model_path) and os.path.isdir(local_model_path):
                self._model_dir = local_model_path
            else:
                try:
                    print("[RAG] 正在通过 ModelScope 检查/下载 BAAI/bge-m3 模型...")
                    self._model_dir = snapshot_download("Xorbits/bge-m3")
                except Exception as e:
                    print(f"[RAG] 连线异常，启动脱机态秒读本地离线仓库缓存: {e}")
                    self._model_dir = os.path.expanduser("~/.cache/modelscope/hub/Xorbits/bge-m3")
            self._embeddings = HuggingFaceEmbeddings(model_name=self._model_dir)
        return self._embeddings

    def build_or_load(self):
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
                safe_docs = []
                for chunk in chunks:
                    sec_res = rag_guard.evaluate_chunk(chunk)
                    if sec_res["is_safe"]:
                        safe_docs.append(Document(page_content=sec_res["content"], metadata=sec_res["metadata"]))
                    else:
                        print(f"[🚨 RAG Security Safeguard] 阻截到疑似投毒数据片段: {os.path.basename(filepath)} | 已扣押至安全审查区！")
                new_docs.extend(safe_docs)
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
            import shutil
            cache_dir = os.path.join(os.path.dirname(__file__), 'chroma_cache')
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
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
        )

    @traceable(name="hybrid_rag_retrieve", run_type="retriever", tags=["rag_retriever", "bm25_chroma", "observability"])
    def retrieve(self, query: str, k=6):
        if self.ensemble_retriever is None:
            self.build_or_load()
            
        self.bm25_retriever.k = k * 2
        self.chroma_retriever.search_kwargs = {"k": k * 2}
        
        # 融入 DFL 动态特征融合层 (自适应计算 Dense/Sparse 权重)
        dense_w, sparse_w, diagnostics = dfl_fusion.calculate_dynamic_weights(query)
        self.ensemble_retriever.weights = [sparse_w, dense_w]
        print(f"[DFL 动态融合层] 调整权重 => Sparse(BM25): {sparse_w}, Dense(BGE-M3): {dense_w} | 诊断: {diagnostics}")
        
        results = self.ensemble_retriever.invoke(query)
        top_docs = results
        
        # 智能去重与重叠切片极速压缩 (Smart Chunk Deduplication & Overlap Merging)
        unique_docs = []
        seen_texts = set()
        for d in top_docs:
            clean_text = d.page_content.strip()
            if not clean_text or clean_text in seen_texts:
                continue
                
            # 探测邻接/包含/高度相似重合段落（清除由 chunk_overlap 或重复语料引发的冗余片段与重复序号）
            is_redundant = False
            for exist_text in list(seen_texts):
                if clean_text in exist_text:
                    is_redundant = True
                    break
                if exist_text in clean_text:
                    # 现阶段候选 Chunk 内容更为详尽完整，直接吞并替换已有残缺子切片
                    seen_texts.remove(exist_text)
                    unique_docs = [doc for doc in unique_docs if doc.page_content.strip() != exist_text]
                    break
                # 基于词集比例的比对，若交集覆盖达到超 65% 的词密度，判定为严重重合切片，舍短留长
                s1 = set(clean_text.split())
                s2 = set(exist_text.split())
                if len(s1 & s2) > 0 and (len(s1 & s2) / min(len(s1), len(s2), 1)) > 0.65:
                    if len(clean_text) <= len(exist_text):
                        is_redundant = True
                        break
                    else:
                        seen_texts.remove(exist_text)
                        unique_docs = [doc for doc in unique_docs if doc.page_content.strip() != exist_text]
                        break
                        
            if not is_redundant:
                seen_texts.add(clean_text)
                unique_docs.append(d)
                if len(unique_docs) >= k:
                    break
        
        sources = []
        for d in unique_docs:
            src = d.metadata.get("source", "Unknown")
            basename = os.path.basename(src)
            if basename not in sources:
                sources.append(basename)
                
        # 拼接精细去重并优化过的新语料上下文，并贴附真实文档标签
        context = "\n\n".join([f"[{d.metadata.get('type', 'doc').upper()} - {d.metadata.get('source', 'Unknown')}] {d.page_content}" for d in unique_docs])
        return context, sources

rag_engine = RAGEngine()
