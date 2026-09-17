"""
FastAPI 后端服务
================
提供 RESTful API 供前端 Web 页面调用
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from rag_engine import HybridRAGEngine
from sample_data import SAMPLE_DOCUMENTS

# ─────────────────────── 全局引擎实例 ───────────────────────
engine: Optional[HybridRAGEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化引擎并加载示例数据"""
    global engine
    engine = HybridRAGEngine()
    # 如果知识库为空，自动加载示例数据
    if engine.get_doc_count() == 0:
        added = engine.add_documents(SAMPLE_DOCUMENTS)
        print(f"✅ 自动加载了 {added} 条示例文档到知识库")
    yield
    print("👋 服务关闭")


# ─────────────────────── FastAPI 应用 ───────────────────────
app = FastAPI(
    title="Hybrid RAG System",
    description="BM25 + 向量检索(ANN) + 重排序(Reranker) 混合检索 RAG 系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─────────────────────── 请求/响应模型 ───────────────────────
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class AskRequest(BaseModel):
    query: str

class AddDocsRequest(BaseModel):
    documents: List[Dict[str, Any]]   # [{"content": str, "metadata": {}}]

class DeleteAllRequest(BaseModel):
    confirm: bool = False


# ─────────────────────── API 路由 ───────────────────────
@app.get("/", include_in_schema=False)
async def index():
    """返回前端页面"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/status")
async def status():
    """系统状态"""
    return {
        "status": "running",
        "doc_count": engine.get_doc_count(),
        "message": f"知识库中共有 {engine.get_doc_count()} 条文档"
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    """
    混合检索 API
    返回：BM25结果、向量检索结果、RRF融合结果、重排序结果
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    if engine.get_doc_count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先添加文档")

    results = engine.hybrid_search(req.query, top_k=req.top_k)
    return {"success": True, "query": req.query, **results}


@app.post("/api/ask")
async def ask(req: AskRequest):
    """
    完整 RAG 问答 API
    返回：检索结果 + LLM 生成的最终答案
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    if engine.get_doc_count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先添加文档")

    result = engine.ask(query=req.query)
    return {"success": True, "query": req.query, **result}


from fastapi.responses import StreamingResponse

class ChatStreamRequest(BaseModel):
    session_id: str = "default"
    query: str
    use_rag: bool = True
    top_k: int = 5

@app.post("/api/v1/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    """
    符合企业架构规范的流式输出 SSE 接口
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    if req.use_rag and engine.get_doc_count() == 0:
        raise HTTPException(status_code=400, detail="知识库为空，请先添加文档")
    
    return StreamingResponse(
        engine.ask_stream(
            query=req.query,
            session_id=req.session_id,
            use_rag=req.use_rag,
            top_k=req.top_k
        ),
        media_type="text/event-stream"
    )



@app.post("/api/documents/add")
async def add_documents(req: AddDocsRequest):
    """添加文档到知识库"""
    if not req.documents:
        raise HTTPException(status_code=400, detail="文档列表不能为空")

    added = engine.add_documents(req.documents)
    return {
        "success": True,
        "added_count": added,
        "total_count": engine.get_doc_count(),
        "message": f"成功添加 {added} 条文档，知识库共 {engine.get_doc_count()} 条"
    }


@app.delete("/api/documents/all")
async def delete_all(req: DeleteAllRequest):
    """清空所有文档"""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="请设置 confirm=true 确认清空操作")
    engine.delete_all()
    return {"success": True, "message": "已清空知识库", "total_count": 0}


@app.get("/api/documents/list")
async def list_documents():
    """列出所有文档"""
    docs = [
        {"id": doc["id"], "content": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
         "metadata": doc["metadata"]}
        for doc in engine.documents
    ]
    return {"success": True, "documents": docs, "total": len(docs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
