import React, { useState, useEffect, useRef } from 'react';
import { 
  Database, UploadCloud, FileText, Trash2, RefreshCw, 
  Search, CheckCircle2, AlertCircle, Clock, HardDrive, 
  Layers, X, FileSpreadsheet, FileCode, Presentation, ShieldCheck,
  Sparkles, Play, Sliders, Zap, Tag
} from 'lucide-react';

export default function KnowledgeManagerModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('docs'); // 'docs' | 'playground'
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [totalDocs, setTotalDocs] = useState(0);
  const [totalSizeFormatted, setTotalSizeFormatted] = useState('0 KB');
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const fileInputRef = useRef(null);

  // RAG 检索演练器状态
  const [playgroundQuery, setPlaygroundQuery] = useState('MCP 模型上下文协议的核心架构与跨进程通讯');
  const [playgroundTopK, setPlaygroundTopK] = useState(4);
  const [playgroundResults, setPlaygroundResults] = useState(null);
  const [playgroundLoading, setPlaygroundLoading] = useState(false);

  const presetQueries = [
    'MCP 模型上下文协议的核心架构与跨进程通讯',
    '企业Token资源平台使用与充值手册',
    '校园一卡通AI变革方案实施路径',
    'RAG 混合检索动态特征融合层 (DFL)',
    '人脸特征识别与活体检测'
  ];

  useEffect(() => {
    if (isOpen) {
      loadDocuments();
      setUploadStatus(null);
    }
  }, [isOpen]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/knowledge/documents');
      const data = await res.json();
      if (data.status === 'success') {
        setDocuments(data.documents || []);
        setTotalDocs(data.total_documents || 0);
        setTotalSizeFormatted(data.total_size_formatted || '0 KB');
      }
    } catch (e) {
      console.error('Failed to load knowledge documents:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploadStatus({
      type: 'uploading',
      message: `正在上传并解析 [${file.name}]...`,
      details: null
    });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/v1/knowledge/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setUploadStatus({
          type: 'success',
          message: data.message,
          details: data.file_info
        });
        loadDocuments();
      } else {
        setUploadStatus({
          type: 'error',
          message: data.detail || data.message || '上传与文档解析失败',
          details: null
        });
      }
    } catch (err) {
      setUploadStatus({
        type: 'error',
        message: `上传发生网络异常: ${err.message}`,
        details: null
      });
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`确定要从知识库中删除文档 [${filename}] 吗？`)) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/knowledge/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        loadDocuments();
      } else {
        alert(data.detail || '删除失败');
      }
    } catch (e) {
      alert(`删除异常: ${e.message}`);
    }
  };

  const handleTriggerReindex = async () => {
    setReindexing(true);
    try {
      const res = await fetch('/api/v1/knowledge/reindex', { method: 'POST' });
      const data = await res.json();
      alert(data.message || '索引更新完成');
      loadDocuments();
    } catch (e) {
      alert(`重构失败: ${e.message}`);
    } finally {
      setReindexing(false);
    }
  };

  const handleRunRetrieval = async (queryText = null) => {
    const q = (queryText !== null ? queryText : playgroundQuery).trim();
    if (!q) return;
    setPlaygroundLoading(true);
    try {
      const res = await fetch('/api/v1/knowledge/test-retrieval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: playgroundTopK })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setPlaygroundResults(data.data);
      } else {
        alert(data.detail || '检索演练失败');
      }
    } catch (e) {
      alert(`检索演练异常: ${e.message}`);
    } finally {
      setPlaygroundLoading(false);
    }
  };

  const getFileIcon = (ext) => {
    switch ((ext || '').toUpperCase()) {
      case 'PDF':
        return <span style={{ color: '#ef4444' }}><FileText size={16} /></span>;
      case 'DOCX':
      case 'DOC':
        return <span style={{ color: '#3b82f6' }}><FileText size={16} /></span>;
      case 'XLSX':
      case 'XLS':
      case 'CSV':
        return <span style={{ color: '#10b981' }}><FileSpreadsheet size={16} /></span>;
      case 'PPTX':
        return <span style={{ color: '#f97316' }}><Presentation size={16} /></span>;
      case 'MD':
      case 'JSON':
      case 'HTML':
      case 'XML':
        return <span style={{ color: '#8b5cf6' }}><FileCode size={16} /></span>;
      default:
        return <span style={{ color: '#94a3b8' }}><FileText size={16} /></span>;
    }
  };

  const filteredDocs = documents.filter(d => 
    d.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.ext.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(10, 15, 29, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--wb-surface-card, #111827)',
        border: '1px solid var(--wb-border-subtle, #1f2937)',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '980px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--wb-border-subtle, #1f2937)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(17, 24, 39, 0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(59, 130, 246, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#3b82f6'
            }}>
              <Database size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright, #f3f4f6)', margin: 0 }}>
                企业私有知识库中心 (Knowledge Base RAG)
              </h2>
              <span style={{ fontSize: '12px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                多格式文档解析、BM25 + BGE-M3 混合向量入库与语义召回演练
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="wb-btn-ghost"
            style={{ padding: '6px', borderRadius: '6px', color: 'var(--wb-text-dim, #9ca3af)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab 导航切换 */}
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '8px 20px',
          borderBottom: '1px solid var(--wb-border-subtle, #1f2937)',
          background: 'rgba(0,0,0,0.15)'
        }}>
          <button
            onClick={() => setActiveTab('docs')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'docs' ? '#3b82f6' : 'transparent',
              color: activeTab === 'docs' ? '#fff' : 'var(--wb-text-dim, #9ca3af)'
            }}
          >
            <Layers size={13} />
            <span>文档资产与上传 ({totalDocs})</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('playground');
              if (!playgroundResults) handleRunRetrieval();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'playground' ? '#3b82f6' : 'transparent',
              color: activeTab === 'playground' ? '#fff' : 'var(--wb-text-dim, #9ca3af)'
            }}
          >
            <Sparkles size={13} />
            <span>即时语义检索演练器 (RAG Playground)</span>
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* TAB 1: 文档资产与上传 */}
          {activeTab === 'docs' && (
            <>
              {/* Top Metric Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--wb-border-subtle, #1f2937)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div style={{ color: '#3b82f6' }}><Layers size={22} /></div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #9ca3af)' }}>已收录文档</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--wb-text-bright, #f3f4f6)' }}>{totalDocs} 篇</div>
                  </div>
                </div>

                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--wb-border-subtle, #1f2937)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div style={{ color: '#10b981' }}><HardDrive size={22} /></div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #9ca3af)' }}>知识库总体积</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--wb-text-bright, #f3f4f6)' }}>{totalSizeFormatted}</div>
                  </div>
                </div>

                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--wb-border-subtle, #1f2937)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div style={{ color: '#8b5cf6' }}><ShieldCheck size={22} /></div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #9ca3af)' }}>向量引擎与防投毒</div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#10b981' }}>BM25 + BGE-M3 (Chroma)</div>
                  </div>
                </div>
              </div>

              {/* Drag and Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                style={{
                  border: `2px dashed ${isDragging ? '#3b82f6' : 'var(--wb-border-subtle, #374151)'}`,
                  background: isDragging ? 'rgba(59, 130, 246, 0.08)' : 'rgba(255, 255, 255, 0.015)',
                  borderRadius: '10px',
                  padding: '20px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileInputChange} 
                  style={{ display: 'none' }} 
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.csv,.json,.pptx,.html,.htm,.xml"
                />
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  background: 'rgba(59, 130, 246, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#3b82f6'
                }}>
                  <UploadCloud size={22} />
                </div>
                <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--wb-text-bright, #f3f4f6)' }}>
                  点击选择 或 将文档直接拖拽至此处
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                  支持 PDF, DOCX, XLSX, TXT, MD, CSV, PPTX, JSON (单文件最大 50MB)
                </div>
              </div>

              {/* Upload Status Card */}
              {uploadStatus && (
                <div style={{
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: uploadStatus.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                  border: `1px solid ${uploadStatus.type === 'error' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                  fontSize: '12.5px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {uploadStatus.type === 'error' ? (
                      <AlertCircle size={15} style={{ color: '#ef4444' }} />
                    ) : (
                      <CheckCircle2 size={15} style={{ color: '#10b981' }} />
                    )}
                    <span style={{ fontWeight: 600, color: uploadStatus.type === 'error' ? '#f87171' : '#34d399' }}>
                      {uploadStatus.message}
                    </span>
                  </div>
                  {uploadStatus.details && (
                    <div style={{ marginTop: '6px', fontSize: '11.5px', color: 'var(--wb-text-dim, #9ca3af)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                      <span>解析分块数: <b style={{ color: '#f3f4f6' }}>{uploadStatus.details.total_chunks}</b> 个</span>
                      <span>提取字符数: <b style={{ color: '#f3f4f6' }}>{uploadStatus.details.total_chars}</b> 字</span>
                      <span>解析耗时: <b style={{ color: '#f3f4f6' }}>{uploadStatus.details.parse_latency_ms}</b> ms</span>
                    </div>
                  )}
                </div>
              )}

              {/* Document Table Section */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ position: 'relative', flex: 1, maxWidth: '320px' }}>
                    <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--wb-text-dim, #9ca3af)' }} />
                    <input
                      type="text"
                      placeholder="搜索知识库文档名称或格式..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px 6px 30px',
                        fontSize: '12px',
                        borderRadius: '6px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--wb-border-subtle, #374151)',
                        color: 'var(--wb-text-bright, #f3f4f6)',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={handleTriggerReindex}
                      disabled={reindexing}
                      className="wb-btn-ghost"
                      style={{
                        padding: '6px 12px',
                        fontSize: '12px',
                        borderRadius: '6px',
                        border: '1px solid var(--wb-border-subtle, #374151)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        color: 'var(--wb-text-bright, #f3f4f6)',
                        cursor: 'pointer'
                      }}
                    >
                      <RefreshCw size={12} className={reindexing ? 'animate-spin' : ''} />
                      <span>{reindexing ? '重构索引中...' : '同步重建向量索引'}</span>
                    </button>
                  </div>
                </div>

                {/* Document List Table */}
                <div style={{
                  border: '1px solid var(--wb-border-subtle, #1f2937)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  maxHeight: '280px',
                  overflowY: 'auto'
                }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ background: 'rgba(255, 255, 255, 0.02)', borderBottom: '1px solid var(--wb-border-subtle, #1f2937)', color: 'var(--wb-text-dim, #9ca3af)' }}>
                        <th style={{ padding: '8px 12px', fontWeight: 500 }}>文档名称</th>
                        <th style={{ padding: '8px 12px', fontWeight: 500 }}>格式</th>
                        <th style={{ padding: '8px 12px', fontWeight: 500 }}>大小</th>
                        <th style={{ padding: '8px 12px', fontWeight: 500 }}>预估切片</th>
                        <th style={{ padding: '8px 12px', fontWeight: 500 }}>更新时间</th>
                        <th style={{ padding: '8px 12px', fontWeight: 500, textAlign: 'right' }}>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loading ? (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                            加载文档资产中...
                          </td>
                        </tr>
                      ) : filteredDocs.length === 0 ? (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '24px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                            暂无匹配的知识库文档
                          </td>
                        </tr>
                      ) : (
                        filteredDocs.map(doc => (
                          <tr 
                            key={doc.id}
                            style={{
                              borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                              transition: 'background 0.15s ease'
                            }}
                          >
                            <td style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--wb-text-bright, #f3f4f6)' }}>
                              {getFileIcon(doc.ext)}
                              <span style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={doc.filename}>
                                {doc.filename}
                              </span>
                            </td>
                            <td style={{ padding: '8px 12px' }}>
                              <span style={{
                                fontSize: '10px',
                                padding: '1px 5px',
                                borderRadius: '4px',
                                background: 'rgba(59, 130, 246, 0.1)',
                                color: '#60a5fa',
                                fontWeight: 600
                              }}>
                                {doc.ext}
                              </span>
                            </td>
                            <td style={{ padding: '8px 12px', color: 'var(--wb-text-dim, #9ca3af)' }}>{doc.size_formatted}</td>
                            <td style={{ padding: '8px 12px', color: 'var(--wb-text-dim, #9ca3af)' }}>{doc.estimated_chunks} 块</td>
                            <td style={{ padding: '8px 12px', color: 'var(--wb-text-dim, #9ca3af)', fontSize: '11px' }}>{doc.updated_at}</td>
                            <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                              <button
                                onClick={() => handleDelete(doc.filename)}
                                className="wb-btn-ghost"
                                title="删除文档"
                                style={{
                                  padding: '3px 6px',
                                  borderRadius: '4px',
                                  color: '#ef4444',
                                  cursor: 'pointer'
                                }}
                              >
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: 即时语义检索演练器 (RAG Playground) */}
          {activeTab === 'playground' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* 搜索演练输入栏 */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--wb-border-subtle, #1f2937)',
                borderRadius: '8px',
                padding: '14px'
              }}>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    value={playgroundQuery}
                    onChange={(e) => setPlaygroundQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleRunRetrieval()}
                    placeholder="输入要进行语义检索的业务问题..."
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      fontSize: '13px',
                      borderRadius: '6px',
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--wb-border-subtle, #374151)',
                      color: 'var(--wb-text-bright, #fff)',
                      outline: 'none'
                    }}
                  />
                  <button
                    onClick={() => handleRunRetrieval()}
                    disabled={playgroundLoading}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      background: '#3b82f6',
                      color: '#fff',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      border: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <Play size={13} />
                    <span>{playgroundLoading ? '召回计算中...' : '开始演练'}</span>
                  </button>
                </div>

                {/* 常用预设提问标签 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginTop: '10px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--wb-text-dim, #9ca3af)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Tag size={11} />
                    <span>预设提问:</span>
                  </span>
                  {presetQueries.map((pq, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setPlaygroundQuery(pq);
                        handleRunRetrieval(pq);
                      }}
                      style={{
                        padding: '2px 8px',
                        fontSize: '11px',
                        borderRadius: '4px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        color: 'var(--wb-text-dim, #9ca3af)',
                        cursor: 'pointer'
                      }}
                    >
                      {pq}
                    </button>
                  ))}
                </div>
              </div>

              {/* 动态特征融合权重卡片 (DFL Diagnostics) */}
              {playgroundResults && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '10px',
                  background: 'rgba(59, 130, 246, 0.04)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  fontSize: '12px'
                }}>
                  <div>
                    <span style={{ color: 'var(--wb-text-dim, #9ca3af)' }}>稠密语义 (BGE-M3): </span>
                    <strong style={{ color: '#60a5fa' }}>{Math.round(playgroundResults.dense_weight * 100)}%</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--wb-text-dim, #9ca3af)' }}>稀疏字面 (BM25): </span>
                    <strong style={{ color: '#34d399' }}>{Math.round(playgroundResults.sparse_weight * 100)}%</strong>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ color: 'var(--wb-text-dim, #9ca3af)' }}>检索耗时: </span>
                    <strong style={{ color: '#fbbf24' }}>{playgroundResults.latency_ms || 35} ms</strong>
                  </div>
                </div>
              )}

              {/* 召回切片结果卡片列表 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '320px', overflowY: 'auto' }}>
                {playgroundLoading ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                    正在执行 BM25 稀疏检索与 BGE-M3 向量相似度混合重排...
                  </div>
                ) : !playgroundResults || playgroundResults.chunks.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                    暂无召回切片结果，请在上方输入问题并点击“开始演练”
                  </div>
                ) : (
                  playgroundResults.chunks.map(chunk => (
                    <div
                      key={chunk.rank}
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--wb-border-subtle, #1f2937)',
                        borderRadius: '8px',
                        padding: '12px 14px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            width: '20px',
                            height: '20px',
                            borderRadius: '4px',
                            background: chunk.rank === 1 ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                            color: chunk.rank === 1 ? '#60a5fa' : 'var(--wb-text-dim, #9ca3af)',
                            fontSize: '11px',
                            fontWeight: 700,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            #{chunk.rank}
                          </span>
                          <span style={{ fontWeight: 600, color: 'var(--wb-text-bright, #fff)', fontSize: '12.5px' }}>
                            {chunk.source}
                          </span>
                          <span style={{
                            fontSize: '9.5px',
                            padding: '1px 5px',
                            borderRadius: '3px',
                            background: 'rgba(255, 255, 255, 0.05)',
                            color: 'var(--wb-text-dim, #9ca3af)'
                          }}>
                            {chunk.type}
                          </span>
                        </div>
                        <span style={{ fontSize: '11px', color: 'var(--wb-text-dim, #9ca3af)' }}>
                          长度: {chunk.length} 字符
                        </span>
                      </div>

                      <div style={{
                        fontSize: '12px',
                        color: 'var(--wb-text-sub, #d1d5db)',
                        lineHeight: 1.6,
                        background: 'rgba(0, 0, 0, 0.2)',
                        padding: '8px 10px',
                        borderRadius: '6px',
                        fontFamily: 'system-ui, -apple-system, sans-serif'
                      }}>
                        {chunk.preview}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid var(--wb-border-subtle, #1f2937)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(17, 24, 39, 0.6)',
          fontSize: '12px',
          color: 'var(--wb-text-dim, #9ca3af)'
        }}>
          <div>知识库具备 DFL 动态融合层与投毒拦截，已接入生产级混合检索管道</div>
          <button
            onClick={onClose}
            style={{
              padding: '6px 16px',
              borderRadius: '6px',
              background: '#3b82f6',
              color: '#ffffff',
              fontSize: '12px',
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer'
            }}
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
