import os
import json
import hashlib
import redis
from langsmith import traceable

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(redis_url)


class SemanticCache:
    def __init__(self, similarity_threshold=0.85):
        self.threshold = similarity_threshold
        self.collection = None
        self.model = None
        self.disabled_reason = ""

    def _ensure_backend(self) -> bool:
        if self.disabled_reason:
            return False
        if self.collection is not None and self.model is not None:
            return True
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            chroma_client = chromadb.PersistentClient(path="./chroma_cache")
            self.collection = chroma_client.get_or_create_collection(
                name="semantic_cache",
                metadata={"hnsw:space": "cosine"},
            )
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            return True
        except BaseException as e:
            self.disabled_reason = str(e)
            print(f"Semantic cache disabled: {e}")
            return False

    def _namespace(self, namespace: str | None) -> str:
        return (namespace or "public").strip()[:180] or "public"

    def _cache_id(self, query: str, namespace: str | None) -> str:
        digest = hashlib.sha256(f"{self._namespace(namespace)}\n{query}".encode("utf-8")).hexdigest()
        return f"{self._namespace(namespace)}:{digest}"

    @traceable(name="semantic_cache_lookup", run_type="tool", tags=["cache", "redis_chroma", "observability"])
    def get_cache(self, query: str, namespace: str | None = None) -> str | None:
        try:
            # 1. Exact match in Redis
            cache_id = self._cache_id(query, namespace)
            exact_match = redis_client.get(f"cache:{cache_id}")
            if exact_match:
                return json.loads(exact_match.decode('utf-8'))

            if not self._ensure_backend():
                return None
            
            # 2. Semantic match in ChromaDB
            query_embedding = self.model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
                where={"namespace": self._namespace(namespace)}
            )
            
            if results and results.get('distances') and len(results['distances'][0]) > 0:
                distance = results['distances'][0][0]
                similarity = 1 - distance
                if similarity >= self.threshold:
                    doc = results['documents'][0][0]
                    return doc
        except BaseException as e:
            print(f"Cache error: {e}")
        return None

    @traceable(name="semantic_cache_store", run_type="tool", tags=["cache_write", "redis_chroma"])
    def set_cache(self, query: str, response: str, namespace: str | None = None) -> None:
        try:
            cache_id = self._cache_id(query, namespace)
            redis_client.setex(f"cache:{cache_id}", 3600, json.dumps(response))
            if not self._ensure_backend():
                return
            query_embedding = self.model.encode(query).tolist()
            self.collection.upsert(
                embeddings=[query_embedding],
                documents=[response],
                ids=[cache_id],
                metadatas=[{"namespace": self._namespace(namespace)}]
            )
        except BaseException as e:
            print(f"Cache set error: {e}")

semantic_cache = SemanticCache()
