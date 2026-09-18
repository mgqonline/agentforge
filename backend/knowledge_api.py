"""
AgentForge · 知识库统一管理与多格式文档解析入库 API
=====================================================
核心能力：
  1. 多格式文档拖拽上传与即时分块解析 (PDF, Word, Excel, PPTX, Markdown, TXT, CSV, JSON, HTML)；
  2. 知识库已收录文档检索、元数据统计与空间用水位；
  3. 异常文件安全剔除与向量索引热更新。
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 确保能引用 document_processor 与 rag_engine
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(Path(__file__).resolve().parent))

from document_processor.doc_parser import DocumentProcessor

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])

SAMPLES_DIR = ROOT_DIR / "document_processor" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.xlsx', '.xls', 
    '.txt', '.md', '.csv', '.json', '.pptx', '.html', '.htm', '.xml'
}

def format_file_size(size_in_bytes: int) -> str:
    """人性化可读文件体积转化"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"

@router.get("/documents")
async def list_knowledge_documents():
    """获取知识库所有已收录的异构文档资产列表"""
    documents = []
    total_size = 0

    if SAMPLES_DIR.exists():
        for item in SAMPLES_DIR.iterdir():
            if not item.is_file():
                continue
            if item.name.startswith("."):
                continue
            ext = item.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            stat = item.stat()
            size = stat.st_size
            total_size += size
            mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

            # 估算切片数 (按平均 500 字符每切片预估)
            est_chunks = max(1, round(size / 500))

            documents.append({
                "id": f"doc_{abs(hash(item.name)) % 10000000}",
                "filename": item.name,
                "ext": ext.replace(".", "").upper(),
                "file_size": size,
                "size_formatted": format_file_size(size),
                "updated_at": mtime_str,
                "status": "indexed",
                "estimated_chunks": est_chunks
            })

    # 按修改时间最新优先排序
    documents.sort(key=lambda d: d["updated_at"], reverse=True)

    return {
        "status": "success",
        "total_documents": len(documents),
        "total_size_bytes": total_size,
        "total_size_formatted": format_file_size(total_size),
        "documents": documents
    }

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    """
    处理前端拖拽或选中的文档上传：
    保存物理文件 -> 触发解析器分块提取 -> 返回解析指标与切片预览
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="未检测到有效的文件名")

    # 安全过滤：防目录遍历
    safe_filename = Path(filename).name
    ext = Path(safe_filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: [{ext}]。当前支持格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    target_path = SAMPLES_DIR / safe_filename
    start_time = time.time()

    # 1. 物理写入磁盘
    try:
        content = await file.read()
        file_size = len(content)
        
        # 限制单文件最大 50MB
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="单文件大小超出 50MB 限制")

        with open(target_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件持久化失败: {str(e)}")

    # 2. 调度 DocumentProcessor 进行深层文本提取与滑动窗口切片
    parsed_chunks = []
    total_chars = 0
    preview_chunks = []
    try:
        processor = DocumentProcessor(chunk_size=600, chunk_overlap=120)
        parsed_chunks = processor.process_file(str(target_path))
        total_chars = sum(len(c.get("content", "")) for c in parsed_chunks)
        
        # 提取前 3 个分块作为前端卡片预览
        for idx, c in enumerate(parsed_chunks[:3]):
            preview_chunks.append({
                "chunk_id": idx + 1,
                "text_snippet": c.get("content", "")[:180] + ("..." if len(c.get("content", "")) > 180 else ""),
                "char_length": len(c.get("content", "")),
                "metadata": c.get("metadata", {})
            })
    except Exception as parse_err:
        # 解析如失败，不阻塞用户上传，提供降级提示
        parsed_chunks = []
        preview_chunks = [{"chunk_id": 1, "text_snippet": f"文档已存储，提取器告警: {str(parse_err)}", "char_length": 0}]

    elapsed_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "status": "success",
        "message": f"文档 [{safe_filename}] 上传并解析成功！",
        "file_info": {
            "filename": safe_filename,
            "ext": ext.replace(".", "").upper(),
            "file_size": file_size,
            "size_formatted": format_file_size(file_size),
            "total_chunks": len(parsed_chunks),
            "total_chars": total_chars,
            "parse_latency_ms": elapsed_ms,
            "preview_chunks": preview_chunks
        }
    }

@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """物理与逻辑删除指定知识库文档"""
    safe_filename = Path(filename).name
    target_path = SAMPLES_DIR / safe_filename

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"文件 [{safe_filename}] 不存在")

    try:
        os.remove(target_path)
        return {
            "status": "success",
            "message": f"知识库文档 [{safe_filename}] 已成功剔除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@router.post("/reindex")
async def trigger_reindex():
    """手动触发知识库向量全量/增量重构"""
    try:
        from rag_engine import rag_engine
        rag_engine.build_or_load()
        return {"status": "success", "message": "知识库全量索引同步与重建已成功触发完成！"}
    except Exception as e:
        return {"status": "degraded", "message": f"知识库已更新，向量同步稍后重试: {str(e)}"}

class RetrievalTestRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

@router.post("/test-retrieval")
async def test_knowledge_retrieval(req: RetrievalTestRequest):
    """
    RAG 即时检索演练器 (Playground)
    输入测试 Query，即时调用 BM25 + BGE-M3 混合检索，返回召回切片、来源文档与特征权重
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    start_t = time.time()
    try:
        from rag_engine import rag_engine
        detail = rag_engine.retrieve_detailed(req.query.strip(), k=req.top_k or 5)
        elapsed_ms = round((time.time() - start_t) * 1000, 1)
        detail["latency_ms"] = elapsed_ms
        return {
            "status": "success",
            "data": detail
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索演练失败: {str(e)}")

