import os
import sys
import jieba
from pathlib import Path
from urllib.parse import urlparse, unquote

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


# 项目根目录（backend 的上一级），用于把语料目录固定为绝对路径
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _default_data_dir() -> str:
    """知识库语料目录的唯一权威定义（绝对路径）。"""
    return os.path.join(_PROJECT_ROOT, 'document_processor', 'samples')


# 只索引这些子目录/前缀；未列入且不符合白名单规则的文件会被跳过。
# 目的：把 grand_project-*.mp3（4.8MB 音频）与大量 test_* 测试数据挡在索引之外，
# 避免真正的业务语料被测试垃圾稀释检索质量。
_INDEX_DENY_DIR_PARTS = {'.agents', 'venv', '.venv', 'chroma_db', '__pycache__', '.git', 'node_modules'}
_INDEX_DENY_FILENAME_PREFIXES = ('test_', 'test-')
_INDEX_DENY_FILENAME_SUBSTRINGS = ('grand_project', 'sample_', 'dummy')
_INDEX_DENY_EXTS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'}


def _should_index_file(path: Path) -> bool:
    """判定某个文件是否应纳入知识库索引（白名单式排除）。"""
    path_str = str(path)
    lowered = path_str.lower()

    for part in _INDEX_DENY_DIR_PARTS:
        if f"{os.sep}{part}{os.sep}" in path_str or path_str.endswith(f"{os.sep}{part}"):
            return False

    name = path.name.lower()
    if name.startswith('.'):
        return False
    if name.startswith(_INDEX_DENY_FILENAME_PREFIXES):
        return False
    if any(token in name for token in _INDEX_DENY_FILENAME_SUBSTRINGS):
        return False
    if path.suffix.lower() in _INDEX_DENY_EXTS:
        return False
    # 忽略 macOS 元数据等杂项
    if lowered.endswith('.ds_store'):
        return False
    return True

class RAGEngine:
    def __init__(self, data_dir=None):
        # 统一使用「绝对路径 + 白名单」定位知识库语料目录。
        # 此前默认值是相对路径 "../document_processor/samples"，依赖进程 CWD；
        # 而 knowledge_api.py / worker.py 各自又算了一份路径，三处容易指向不同目录。
        self.data_dir = data_dir or _default_data_dir()
        self.persist_dir = os.path.join(os.path.dirname(__file__), 'chroma_db')
        self._embeddings = None
        self._model_dir = None
        self.ensemble_retriever = None
        # 索引健康状态：供上层区分「正常」与「降级」，避免静默失败被长期忽略
        self.status = "uninitialized"
        self.status_detail = ""
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
            
        conn = None
        cursor = None
        try:
            database_url = os.getenv("DATABASE_URL") or os.getenv("ASYNC_DATABASE_URL")
            if not database_url:
                raise RuntimeError("DATABASE_URL or ASYNC_DATABASE_URL must be configured")
            parsed_db = urlparse(database_url)
            if parsed_db.scheme.startswith("postgresql"):
                conn = psycopg2.connect(
                    dbname=parsed_db.path.lstrip("/") or "ailearning",
                    user=parsed_db.username or "aiuser",
                    # 连接串里的口令是百分号编码的（# -> %23、@ -> %40 等），
                    # urlparse 不会自动解码，必须显式 unquote，否则含特殊字符的
                    # 强密码会以编码态送进数据库导致 password authentication failed。
                    password=unquote(parsed_db.password) if parsed_db.password else "",
                    host=parsed_db.hostname or "localhost",
                    port=parsed_db.port or 5432,
                )
            else:
                raise ValueError("RAG document index requires a PostgreSQL DATABASE_URL")
            cursor = conn.cursor()
            # 兜底建表：迁移 004 会创建它，但部署顺序未必可靠（例如先起服务后跑迁移）。
            # 这里做幂等补建，确保「知识库可用」不依赖外部执行顺序。
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_hashes (
                    id BIGSERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL UNIQUE,
                    md5_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            conn.commit()
        except Exception as e:
            # 显式记录降级状态。此前这里只打印一句"无缝切换"，让调用方误以为一切正常，
            # 实际文档指纹表缺失导致检索能力整体失效却无人察觉。
            self.status = "degraded"
            self.status_detail = f"Postgres 不可用，已降级为本地 Chroma + BM25 缓存模式: {e}"
            print(f"[RAG] ⚠️ 降级运行（知识库检索质量下降）: {e}")
            vectorstore = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
            self.chroma_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            import pickle
            bm25_path = os.path.join(self.persist_dir, 'bm25.pickle')
            if os.path.exists(bm25_path):
                with open(bm25_path, 'rb') as f:
                    self.bm25_retriever = pickle.load(f)
            else:
                fallback_docs = [Document(page_content="知识库索引为空或不可用，请检查数据库、向量索引和模型缓存状态。", metadata={"source": "system_fallback", "rag_status": "degraded"})]
                self.bm25_retriever = BM25Retriever.from_documents(fallback_docs)
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.chroma_retriever],
                weights=[0.5, 0.5]
            )
            return
            
        cursor.execute("SELECT filepath, md5_hash FROM document_hashes")
        db_hashes = {row[0]: row[1] for row in cursor.fetchall()}
        
        current_files = {}
        for ext in self.supported_exts:
            for path in Path(self.data_dir).rglob(f'*{ext}'):
                # 白名单式过滤：排除测试数据、音频、缓存目录等非业务语料
                if not _should_index_file(path):
                    continue
                current_files[str(path)] = compute_md5(str(path))
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
                fallback_docs = [Document(page_content="BM25 索引缺失；当前无法提供关键词检索结果。", metadata={"source": "system_fallback", "rag_status": "degraded"})]
                self.bm25_retriever = BM25Retriever.from_documents(fallback_docs)
                
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.chroma_retriever],
                weights=[0.5, 0.5]
            )
            self.status = "ok"
            self.status_detail = "索引无变更，已直接加载现有向量与 BM25 索引"
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
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.Redis.from_url(redis_url)
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
        self.status = "ok"
        self.status_detail = f"增量重建完成: 新增 {len(added)}, 修改 {len(modified)}, 删除 {len(deleted)}"

    def get_status(self) -> dict:
        """暴露索引健康状态，供 /health 与知识库接口区分「正常」与「降级」。"""
        return {
            "status": self.status,
            "detail": self.status_detail,
            "ready": self.ensemble_retriever is not None,
            "data_dir": self.data_dir,
            "degraded": self.status == "degraded",
        }

    def has_pending_changes(self) -> bool:
        """检测语料目录相对索引指纹是否有变更（供上传后自动增量索引用）。"""
        import hashlib
        conn = None
        cursor = None
        try:
            import psycopg2
            database_url = os.getenv("DATABASE_URL") or os.getenv("ASYNC_DATABASE_URL")
            if not database_url:
                return True
            parsed_db = urlparse(database_url)
            conn = psycopg2.connect(
                dbname=parsed_db.path.lstrip("/") or "ailearning",
                user=parsed_db.username or "aiuser",
                password=unquote(parsed_db.password) if parsed_db.password else "",
                host=parsed_db.hostname or "localhost",
                port=parsed_db.port or 5432,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT filepath, md5_hash FROM document_hashes")
            db_hashes = {row[0]: row[1] for row in cursor.fetchall()}

            current = {}
            for ext in self.supported_exts:
                for path in Path(self.data_dir).rglob(f'*{ext}'):
                    if not _should_index_file(path):
                        continue
                    h = hashlib.md5()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            h.update(chunk)
                    current[str(path)] = h.hexdigest()

            for fp, md5 in current.items():
                if db_hashes.get(fp) != md5:
                    return True
            for fp in db_hashes:
                if fp not in current:
                    return True
            return False
        except Exception:
            # 无法判定时按「有变更」处理，宁可多重建一次也不漏掉新上传的文档
            return True
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception:
                pass

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

    def retrieve_detailed(self, query: str, k: int = 5):
        """面向 RAG 演练器提供结构化切片召回元数据、权重诊断与文档溯源"""
        if self.ensemble_retriever is None:
            self.build_or_load()
            
        dense_w, sparse_w, diagnostics = dfl_fusion.calculate_dynamic_weights(query)
        self.ensemble_retriever.weights = [sparse_w, dense_w]
        
        try:
            results = self.ensemble_retriever.invoke(query)
        except Exception as e:
            results = []
            print(f"[RAG Playground] 检索异常: {e}")
            
        chunks = []
        seen = set()
        for d in results:
            content = d.page_content.strip()
            if not content or content in seen:
                continue
            seen.add(content)
            src = d.metadata.get("source", "Unknown")
            basename = os.path.basename(src)
            chunks.append({
                "rank": len(chunks) + 1,
                "source": basename,
                "type": d.metadata.get("type", "doc").upper(),
                "content": content,
                "preview": content[:260] + ("..." if len(content) > 260 else ""),
                "length": len(content),
                "metadata": d.metadata
            })
            if len(chunks) >= k:
                break
                
        return {
            "query": query,
            "dense_weight": dense_w,
            "sparse_weight": sparse_w,
            "diagnostics": diagnostics,
            "total_recalled": len(chunks),
            "chunks": chunks
        }

rag_engine = RAGEngine()

