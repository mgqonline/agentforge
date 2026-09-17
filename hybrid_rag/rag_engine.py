import os
import re
import math
import json
import jieba
import threading
import numpy as np
import chromadb
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from rank_bm25 import BM25Okapi
from openai import OpenAI
from dotenv import load_dotenv

from modelscope import snapshot_download
from sentence_transformers import SentenceTransformer, CrossEncoder

load_dotenv()

TOP_K       = 5
RRF_K       = 60
CHROMA_DIR  = './chroma_db'   # ChromaDB 持久化目录


# ─────────────────────── 工具函数 ───────────────────────
def tokenize_zh(text: str) -> List[str]:
    """jieba 中英文分词"""
    tokens = list(jieba.cut(text))
    return [t for t in tokens if t.strip() and not re.match(r'^[^\w\u4e00-\u9fff]+$', t)]


def reciprocal_rank_fusion(results_list: List[List[Dict]], k: int = RRF_K) -> List[Dict]:
    """RRF 倒数排名融合"""
    scores: Dict[str, float] = {}
    docs_map: Dict[str, Dict] = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            doc_id = doc['id']
            docs_map[doc_id] = doc
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [{**docs_map[did], 'rrf_score': round(scores[did], 6)} for did in sorted_ids]


# ─────────────────────── 主引擎 ───────────────────────
class HybridRAGEngine:

    def __init__(self):
        print('🚀 初始化 Hybrid RAG Engine (ChromaDB + BAAI/bge-m3 Dense Embedding)...')

        self._lock = threading.Lock()
        self.sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)

        # 1. 深度 Embedding 模型 (Xorbits/bge-m3，本地缓存就绪)
        print('   📦 加载 Xorbits/bge-m3 Embedding 模型...')
        emb_model_dir = snapshot_download('Xorbits/bge-m3')
        self.embedder = SentenceTransformer(emb_model_dir)


        # 2. 持久化 ChromaDB
        print('   🗄️ 初始化 Chroma Vector Database...')
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.chroma_client.get_or_create_collection(
            name="hybrid_rag_docs",
            metadata={"hnsw:space": "cosine"}
        )

        # BM25 内存索引（自动基于 ChromaDB 加载的文档构建）
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict] = []

        # 3. DeepSeek LLM
        api_key = os.environ.get('DEEPSEEK_API_KEY', 'dummy-placeholder')
        self.llm_client = OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com/v1',
        )

        # 4. Reranker 模型 (BAAI/bge-reranker-base)
        print('   📦 初始化 CrossEncoder Rerank 模型...')
        rerank_model_dir = snapshot_download('BAAI/bge-reranker-base')
        self.reranker = CrossEncoder(rerank_model_dir)

        # 恢复索引
        self._sync_documents_and_rebuild_bm25()
        print(f'✅ RAG Engine 就绪！知识库共 {len(self.documents)} 条文档\n')

    def _sync_documents_and_rebuild_bm25(self):
        """同步 ChromaDB 中的所有文档并重组内存 BM25 索引"""
        chroma_res = self.collection.get()
        ids = chroma_res.get('ids', [])
        documents = chroma_res.get('documents', [])
        metadatas = chroma_res.get('metadatas', [])

        self.documents = [
            {'id': ids[i], 'content': documents[i], 'metadata': metadatas[i] or {}}
            for i in range(len(ids))
        ]

        if self.documents:
            tokenized_corpus = [tokenize_zh(doc['content']) for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            self.bm25 = None

    # ────────────────── 文档管理 ──────────────────
    def add_documents(self, docs: List[Dict[str, Any]]) -> int:
        with self._lock:
            existing_contents = {doc['content'] for doc in self.documents}
            new_ids, new_contents, new_metadatas, new_embeddings = [], [], [], []

            for doc in docs:
                content = doc.get('content', '').strip()
                if not content or content in existing_contents:
                    continue
                doc_id = f"doc_{abs(hash(content)) % 10**10}"
                meta = doc.get('metadata', {})

                new_ids.append(doc_id)
                new_contents.append(content)
                new_metadatas.append(meta)
                existing_contents.add(content)

            if new_contents:
                # 计算高精度 Dense Vector
                embeddings = self.embedder.encode(new_contents, normalize_embeddings=True).tolist()
                self.collection.add(
                    ids=new_ids,
                    documents=new_contents,
                    metadatas=new_metadatas,
                    embeddings=embeddings
                )
                self._sync_documents_and_rebuild_bm25()
                return len(new_contents)

            return 0

    def delete_all(self):
        with self._lock:
            self.chroma_client.delete_collection("hybrid_rag_docs")
            self.collection = self.chroma_client.get_or_create_collection(
                name="hybrid_rag_docs",
                metadata={"hnsw:space": "cosine"}
            )
            self.documents = []
            self.bm25 = None

    def get_doc_count(self) -> int:
        return len(self.documents)

    # ────────────────── 三路检索 ──────────────────
    def bm25_search(self, query: str, top_k: int = TOP_K) -> List[Dict]:
        if not self.bm25 or not self.documents:
            return []
        tokens = tokenize_zh(query)
        scores = self.bm25.get_scores(tokens)
        ranked = np.argsort(scores)[::-1][:top_k]
        return [{
            'id': self.documents[i]['id'],
            'content': self.documents[i]['content'],
            'metadata': self.documents[i]['metadata'],
            'bm25_score': round(float(scores[i]), 4),
            'source': 'BM25',
        } for i in ranked]

    def vector_search(self, query: str, top_k: int = TOP_K) -> List[Dict]:
        if self.get_doc_count() == 0:
            return []

        # 用 bge-m3 计算 query vector
        query_emb = self.embedder.encode([query], normalize_embeddings=True).tolist()
        res = self.collection.query(
            query_embeddings=query_emb,
            n_results=min(top_k, self.get_doc_count())
        )

        results = []
        if res and res.get('ids') and res['ids'][0]:
            for i in range(len(res['ids'][0])):
                doc_id = res['ids'][0][i]
                content = res['documents'][0][i]
                meta = res['metadatas'][0][i] or {}
                # 余弦距离转成相似度分值
                dist = res['distances'][0][i] if res.get('distances') else 0.0
                sim_score = round(1.0 - dist, 4)

                results.append({
                    'id': doc_id,
                    'content': content,
                    'metadata': meta,
                    'vector_score': sim_score,
                    'source': 'bge-m3 Dense Vector'
                })

        return results


    def rerank(self, query: str, candidates: List[Dict], top_k: int = TOP_K) -> List[Dict]:
        """使用 BAAI/bge-reranker-base 进行真正的深度重排序"""
        if not candidates:
            return []
        
        # 组装问题和候选文档的文本对
        pairs = [[query, doc['content']] for doc in candidates]
        
        # 批量计算分数
        scores = self.reranker.predict(pairs)
        
        for i, doc in enumerate(candidates):
            doc['rerank_score'] = round(float(scores[i]), 4)
            
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_k]

    def hybrid_search(self, query: str, top_k: int = TOP_K) -> Dict[str, Any]:
        bm25_results   = self.bm25_search(query, top_k=top_k * 2)
        vector_results = self.vector_search(query, top_k=top_k * 2)
        rrf_results    = reciprocal_rank_fusion([bm25_results, vector_results])
        reranked       = self.rerank(query, rrf_results[:top_k * 2], top_k=top_k)
        return {
            'bm25_results':     bm25_results[:top_k],
            'vector_results':   vector_results[:top_k],
            'rrf_results':      rrf_results[:top_k],
            'reranked_results': reranked,
        }

    # ────────────────── RAG 生成 ──────────────────
    def generate_answer(self, query: str, contexts: List[str], session_id: str = "default") -> str:
        real_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not real_key or real_key == 'dummy-placeholder':
            top_ctx = contexts[0] if contexts else '未找到相关内容'
            return f'ℹ️ [未配置 DEEPSEEK_API_KEY，以下为检索摘要]\n\n{top_ctx}'

        messages = [{'role': 'system', 'content': '你是精准的知识问答助手，请结合会话上下文与知识库严格回答，不编造内容。'}]
        # 融入历史会话（保留最近 6 条）
        history = self.sessions[session_id][-6:]
        messages.extend(history)

        if contexts:
            context_text = '\n\n---\n\n'.join([f'[来源{i+1}] {ctx}' for i, ctx in enumerate(contexts)])
            user_content = f'上下文：\n{context_text}\n\n问题：{query}'
        else:
            user_content = query

        messages.append({'role': 'user', 'content': user_content})

        try:
            resp = self.llm_client.chat.completions.create(
                model='deepseek-chat',
                messages=messages,
                temperature=0.1, max_tokens=1024,
            )
            answer = resp.choices[0].message.content
            # 记录历史
            self.sessions[session_id].append({'role': 'user', 'content': query})
            self.sessions[session_id].append({'role': 'assistant', 'content': answer})
            return answer
        except Exception as e:
            return f'❌ LLM 调用失败: {str(e)}'

    def ask(self, query: str, session_id: str = "default", use_rag: bool = True, top_k: int = TOP_K) -> Dict[str, Any]:
        if use_rag and self.get_doc_count() > 0:
            results   = self.hybrid_search(query, top_k=top_k)
            top_docs  = results['reranked_results'][:top_k]
            contexts  = [d['content'] for d in top_docs]
        else:
            results  = {'bm25_results': [], 'vector_results': [], 'rrf_results': [], 'reranked_results': []}
            contexts = []

        answer = self.generate_answer(query, contexts, session_id=session_id)
        return {**results, 'answer': answer, 'contexts_used': contexts, 'session_id': session_id}

    def ask_stream(self, query: str, session_id: str = "default", use_rag: bool = True, top_k: int = TOP_K):
        """流式回答生成 (Server-Sent Events 格式)，支持 Session 隔离与动态 RAG 控制"""
        real_key = os.environ.get('DEEPSEEK_API_KEY', '')
        
        if use_rag and self.get_doc_count() > 0:
            results = self.hybrid_search(query, top_k=top_k)
            top_docs = results['reranked_results'][:top_k]
            contexts = [d['content'] for d in top_docs]
        else:
            contexts = []
        
        if not real_key or real_key == 'dummy-placeholder':
            top_ctx = contexts[0] if contexts else '未找到相关内容'
            msg = f'ℹ️ [未配置 DEEPSEEK_API_KEY，以下为检索摘要]\n\n{top_ctx}'
            self.sessions[session_id].append({'role': 'user', 'content': query})
            self.sessions[session_id].append({'role': 'assistant', 'content': msg})
            data = json.dumps({"id": "mock", "content": msg, "role": "assistant"}, ensure_ascii=False)
            yield f'data: {data}\n\n'
            yield 'data: [DONE]\n\n'
            return


        messages = [{'role': 'system', 'content': '你是精准的知识问答助手，请结合会话上下文与知识库严格回答，不编造内容。'}]
        # 融入历史会话（保留最近 6 条）
        history = self.sessions[session_id][-6:]
        messages.extend(history)

        if contexts:
            context_text = '\n\n---\n\n'.join([f'[来源{i+1}] {ctx}' for i, ctx in enumerate(contexts)])
            user_content = f'上下文：\n{context_text}\n\n问题：{query}'
        else:
            user_content = query

        messages.append({'role': 'user', 'content': user_content})
        full_answer = []

        try:
            resp = self.llm_client.chat.completions.create(
                model='deepseek-chat',
                messages=messages,
                temperature=0.1, max_tokens=1024,
                stream=True
            )
            for chunk in resp:
                content = chunk.choices[0].delta.content or ""
                if content:
                    full_answer.append(content)
                    data = json.dumps({"id": chunk.id, "content": content, "role": "assistant"}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            # 存储历史
            complete_text = "".join(full_answer)
            self.sessions[session_id].append({'role': 'user', 'content': query})
            self.sessions[session_id].append({'role': 'assistant', 'content': complete_text})

            yield "data: [DONE]\n\n"
        except Exception as e:
            err_data = json.dumps({"id": "error", "content": f"❌ LLM 调用失败: {str(e)}", "role": "assistant"}, ensure_ascii=False)
            yield f"data: {err_data}\n\n"
            yield "data: [DONE]\n\n"

