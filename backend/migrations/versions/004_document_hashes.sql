-- ============================================================================
-- 004_document_hashes
-- 知识库（RAG）文档增量索引指纹表
-- ----------------------------------------------------------------------------
-- 背景：rag_engine.build_or_load() 依赖此表来判定文档的新增/修改/删除，
--       从而决定是否需要重新向量化。但此前全仓库没有任何代码创建它，
--       导致 build_or_load() 在 SELECT 阶段就抛 UndefinedTable 异常，
--       ensemble_retriever 始终为 None，知识库检索能力整体失效。
-- 本迁移补齐该表，使知识库增量索引链路可用。
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_hashes (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    -- 用绝对路径作为唯一键：同一个文件名可能出现在不同目录，不能用 filename 去重
    filepath TEXT NOT NULL UNIQUE,
    md5_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 按文件名检索（删除/更新向量时按 basename 定位）
CREATE INDEX IF NOT EXISTS idx_document_hashes_filename
    ON document_hashes (filename);

-- 按最近更新时间巡检
CREATE INDEX IF NOT EXISTS idx_document_hashes_updated
    ON document_hashes (updated_at DESC);