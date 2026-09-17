import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Target, BookOpen, CheckSquare, Square, FileCode, 
  ChevronLeft, Sparkles, Lightbulb, ShieldCheck, ArrowRight,
  HelpCircle, Code2, ListOrdered, Download, Printer, Check, ChevronDown, FileText,
  ZoomIn, ZoomOut, Maximize2, X, Search, Play, Copy, Terminal, Eye
} from 'lucide-react';

const ZOOM_LEVELS = [0.85, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0];

export default function MissionGuide({
  phaseDetail = null,
  activePhaseTitle = '',
  isCollapsed = false,
  codeFiles = [],
  activeCodeFile = null,
  onSelectCodeFile = () => {},
  onToggleCollapse = () => {},
  onLoadStarterCode = () => {}
}) {
  const [activeTab, setActiveTab] = useState('mission'); // 'mission' | 'doc'
  const [checklist, setChecklist] = useState([]);
  const [isHintExpanded, setIsHintExpanded] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportSuccessToast, setExportSuccessToast] = useState(null);
  const exportMenuRef = useRef(null);

  // 实战脚本文件库搜索与交互状态
  const [codeSearchQuery, setCodeSearchQuery] = useState('');
  const [expandedPreviewFile, setExpandedPreviewFile] = useState(null);
  const [isFilesDrawerExpanded, setIsFilesDrawerExpanded] = useState(true);
  const [copiedFile, setCopiedFile] = useState(null);

  // 知识手册字号缩放比例 (默认 1.0，持久化至 localStorage)
  const [docZoom, setDocZoom] = useState(() => {
    try {
      const saved = localStorage.getItem('agentforge_guide_zoom');
      const val = saved ? parseFloat(saved) : 1.0;
      return ZOOM_LEVELS.includes(val) ? val : 1.0;
    } catch {
      return 1.0;
    }
  });

  // 全屏沉浸式宽屏研读模式
  const [isZenMode, setIsZenMode] = useState(false);

  // 监听 ESC 键关闭全屏沉浸研读
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isZenMode) {
        setIsZenMode(false);
      }
    };
    if (isZenMode) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isZenMode]);

  const handleZoomIn = () => {
    setDocZoom(prev => {
      const next = ZOOM_LEVELS.find(z => z > prev + 0.01) || ZOOM_LEVELS[ZOOM_LEVELS.length - 1];
      try { localStorage.setItem('agentforge_guide_zoom', String(next)); } catch {}
      return next;
    });
  };

  const handleZoomOut = () => {
    setDocZoom(prev => {
      const reversed = [...ZOOM_LEVELS].reverse();
      const next = reversed.find(z => z < prev - 0.01) || ZOOM_LEVELS[0];
      try { localStorage.setItem('agentforge_guide_zoom', String(next)); } catch {}
      return next;
    });
  };

  const handleZoomReset = () => {
    setDocZoom(1.0);
    try { localStorage.setItem('agentforge_guide_zoom', '1.0'); } catch {}
  };

  // 点击外部收起导出下拉框
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) {
        setShowExportMenu(false);
      }
    };
    if (showExportMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showExportMenu]);

  useEffect(() => {
    if (phaseDetail && phaseDetail.checklist) {
      setChecklist(phaseDetail.checklist);
    }
  }, [phaseDetail]);

  const toggleCheck = (idx) => {
    setChecklist(prev => prev.map((item, i) => i === idx ? { ...item, done: !item.done } : item));
  };

  // 1. 导出完整 Markdown 讲义
  const handleExportMarkdown = (missionObj) => {
    setShowExportMenu(false);
    if (!phaseDetail) return;

    const title = phaseDetail.title || phaseDetail.id;
    const starterCode = phaseDetail.starter_code || '';
    const solutionCode = phaseDetail.solution_code || starterCode;
    const testCode = phaseDetail.test_code || '';
    const guideMd = phaseDetail.guide_markdown || '无详细知识手册说明。';
    const prereqs = phaseDetail.prerequisites || [];

    const content = [
      `# AI Learning Lab 实战讲义：${title}`,
      `> 阶段代号：${phaseDetail.id} | 导出时间：${new Date().toLocaleString()} | AI 全栈实战平台`,
      ``,
      `---`,
      ``,
      `## 🎯 一、 闯关实战挑战目标`,
      `- **核心任务**：${missionObj.mission_title}`,
      `- **实战目标**：${missionObj.mission_goal}`,
      prereqs.length > 0 ? `- **前置依赖**：${prereqs.join(', ')}` : `- **前置依赖**：无（新手推荐首关）`,
      ``,
      `### 1. 业务需求契约规范`,
      ...(missionObj.requirements || []).map((r, i) => `${i + 1}. ${r}`),
      ``,
      `### 2. 四步实战演进指引`,
      ...(missionObj.learning_steps || []).map(s => `- ${s}`),
      ``,
      `### 3. 自动化验收断言标准`,
      `> ${missionObj.acceptance_criteria}`,
      ``,
      `---`,
      ``,
      `## 📖 二、 核心知识手册与架构深度解析`,
      guideMd,
      ``,
      `---`,
      ``,
      `## 💡 三、 官方标准参考实现 (Clean Code)`,
      `\`\`\`python`,
      solutionCode.trim(),
      `\`\`\``,
      ``,
      `---`,
      ``,
      `## 🧪 四、 自动化单元评测套件`,
      `\`\`\`python`,
      testCode.trim(),
      `\`\`\``,
      ``,
      `---`,
      `*本讲义由 AI Learning Lab 企业级工程师实战平台导出生成，仅供技术沉淀与离线研读。*`
    ].join('\n');

    try {
      const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${phaseDetail.id}_handbook.md`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportSuccessToast('讲义已成功导出为 Markdown 文件！');
      setTimeout(() => setExportSuccessToast(null), 3000);
    } catch (e) {
      alert('导出讲义失败: ' + e.message);
    }
  };

  // 2. 唤醒浏览器原生打印/PDF导出
  const handlePrintHandbook = () => {
    setShowExportMenu(false);
    window.print();
  };

  if (!phaseDetail) {
    return (
      <section className={`wb-guide-pane ${isCollapsed ? 'collapsed' : ''}`} style={{ padding: '24px', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--wb-text-dim)', fontSize: '12px' }}>加载关卡指南中...</div>
      </section>
    );
  }

  const mission = phaseDetail.mission || {
    mission_title: `实战挑战：${phaseDetail.title || '核心技术落地'}`,
    mission_goal: '掌握当前阶段的核心工程设计，根据右侧模板完善关键实现并运行通过单元测试。',
    requirements: [
      '在右侧编辑器中阅读并完善核心代码逻辑',
      '确保接口定义规范，通过所有单元测试断言'
    ],
    learning_steps: [
      '第 1 步【学习手册】：切换至【知识手册】Tab，深入理解核心原理与设计规范；',
      '第 2 步【编写实现】：在右侧编辑器中补充完成目标函数/模块；',
      '第 3 步【沙箱调试】：点击【运行】(⌘↵) 观察输出，遇困惑使用【AI 伴学诊断】；',
      '第 4 步【验证通关】：点击【验证通关】，通过自动化测试点亮本关并斩获经验！'
    ],
    acceptance_criteria: '自动化测试将针对核心逻辑进行多维度断言，确保结果符合契约。',
    hint: '先理清输入输出参数契约，善用【AI 伴学诊断】获取针对性代码指导。'
  };

  // 缩放控制胶囊条
  const renderZoomControls = (isModal = false) => (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '2px',
      background: isModal ? 'var(--wb-bg-subtle)' : 'var(--wb-bg-subtle)',
      border: '1px solid var(--wb-border-subtle)',
      borderRadius: '5px',
      padding: '1px 3px',
      userSelect: 'none'
    }}>
      <button
        onClick={handleZoomOut}
        disabled={docZoom <= ZOOM_LEVELS[0]}
        title={`缩小手册字号 (当前: ${Math.round(docZoom * 100)}%)`}
        style={{
          background: 'transparent',
          border: 'none',
          color: docZoom <= ZOOM_LEVELS[0] ? 'var(--wb-text-dim)' : 'var(--wb-text-bright)',
          cursor: docZoom <= ZOOM_LEVELS[0] ? 'not-allowed' : 'pointer',
          padding: '2px 4px',
          borderRadius: '3px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: docZoom <= ZOOM_LEVELS[0] ? 0.35 : 1
        }}
        onMouseEnter={(e) => { if (docZoom > ZOOM_LEVELS[0]) e.currentTarget.style.background = 'var(--wb-bg-hover)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <ZoomOut size={12} />
      </button>

      <button
        onClick={handleZoomReset}
        title="点击恢复为 100% 默认大小"
        style={{
          background: 'transparent',
          border: 'none',
          color: docZoom !== 1.0 ? 'var(--wb-accent-subtle)' : 'var(--wb-text-sub)',
          fontWeight: docZoom !== 1.0 ? 700 : 500,
          cursor: 'pointer',
          padding: '1px 3px',
          fontSize: '10.5px',
          fontFamily: 'var(--wb-font-mono)',
          minWidth: '36px',
          textAlign: 'center',
          borderRadius: '3px'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--wb-bg-hover)'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        {Math.round(docZoom * 100)}%
      </button>

      <button
        onClick={handleZoomIn}
        disabled={docZoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
        title={`放大手册字号 (当前: ${Math.round(docZoom * 100)}%)`}
        style={{
          background: 'transparent',
          border: 'none',
          color: docZoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1] ? 'var(--wb-text-dim)' : 'var(--wb-text-bright)',
          cursor: docZoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1] ? 'not-allowed' : 'pointer',
          padding: '2px 4px',
          borderRadius: '3px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: docZoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1] ? 0.35 : 1
        }}
        onMouseEnter={(e) => { if (docZoom < ZOOM_LEVELS[ZOOM_LEVELS.length - 1]) e.currentTarget.style.background = 'var(--wb-bg-hover)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <ZoomIn size={12} />
      </button>

      {!isModal && (
        <>
          <div style={{ width: '1px', height: '10px', background: 'var(--wb-border-subtle)', margin: '0 1px' }} />
          <button
            onClick={() => setIsZenMode(true)}
            title="开启宽屏/全屏沉浸研读模式"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--wb-text-sub)',
              cursor: 'pointer',
              padding: '2px 4px',
              borderRadius: '3px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--wb-bg-hover)';
              e.currentTarget.style.color = 'var(--wb-text-bright)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--wb-text-sub)';
            }}
          >
            <Maximize2 size={11} />
          </button>
        </>
      )}
    </div>
  );

  // Markdown 自适应等比缩放渲染器
  const renderMarkdownContent = (markdownText, currentZoom = 1.0) => (
    <div style={{ 
      fontSize: `${Math.round(13 * currentZoom)}px`, 
      lineHeight: currentZoom > 1.25 ? '1.8' : '1.7', 
      color: 'var(--wb-text-sub)',
      transition: 'font-size 0.15s ease, line-height 0.15s ease'
    }}>
      <ReactMarkdown
        components={{
          h1: ({node, ...props}) => (
            <h1 
              style={{ 
                fontSize: `${Math.round(17 * currentZoom)}px`, 
                fontWeight: 700, 
                color: 'var(--wb-text-bright)', 
                borderBottom: '1px solid var(--wb-border-subtle)', 
                paddingBottom: `${Math.round(6 * currentZoom)}px`, 
                margin: `${Math.round(18 * currentZoom)}px 0 ${Math.round(10 * currentZoom)}px`,
                letterSpacing: '-0.01em'
              }} 
              {...props} 
            />
          ),
          h2: ({node, ...props}) => (
            <h2 
              style={{ 
                fontSize: `${Math.round(14.5 * currentZoom)}px`, 
                fontWeight: 650, 
                color: 'var(--wb-text-bright)', 
                margin: `${Math.round(16 * currentZoom)}px 0 ${Math.round(8 * currentZoom)}px`,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }} 
              {...props} 
            />
          ),
          h3: ({node, ...props}) => (
            <h3 
              style={{ 
                fontSize: `${Math.round(13.2 * currentZoom)}px`, 
                fontWeight: 600, 
                color: 'var(--wb-text-sub)', 
                margin: `${Math.round(14 * currentZoom)}px 0 ${Math.round(6 * currentZoom)}px` 
              }} 
              {...props} 
            />
          ),
          p: ({node, ...props}) => (
            <p style={{ marginBottom: `${Math.round(11 * currentZoom)}px` }} {...props} />
          ),
          pre: ({node, ...props}) => (
            <pre 
              style={{ 
                background: 'var(--wb-bg-subtle)', 
                padding: `${Math.round(11 * currentZoom)}px`, 
                borderRadius: '6px', 
                overflowX: 'auto', 
                border: '1px solid var(--wb-border-subtle)', 
                margin: `${Math.round(10 * currentZoom)}px 0`,
                fontSize: `${Math.round(12 * currentZoom)}px`,
                lineHeight: '1.55'
              }} 
              {...props} 
            />
          ),
          code: ({node, className, children, ...props}) => {
            const isBlock = String(children).includes('\n') || (className && className.includes('language-'));
            const codeFontSize = `${Math.round(12 * currentZoom)}px`;
            return isBlock ? (
              <code style={{ fontFamily: 'var(--wb-font-mono)', fontSize: codeFontSize, color: 'var(--wb-text-bright)' }} {...props}>
                {children}
              </code>
            ) : (
              <code style={{ background: 'var(--wb-bg-hover)', padding: '1.5px 5px', borderRadius: '3px', color: 'var(--wb-text-bright)', fontFamily: 'var(--wb-font-mono)', fontSize: codeFontSize }} {...props}>
                {children}
              </code>
            );
          },
          ul: ({node, ...props}) => (
            <ul style={{ paddingLeft: `${Math.round(20 * currentZoom)}px`, marginBottom: `${Math.round(10 * currentZoom)}px` }} {...props} />
          ),
          ol: ({node, ...props}) => (
            <ol style={{ paddingLeft: `${Math.round(20 * currentZoom)}px`, marginBottom: `${Math.round(10 * currentZoom)}px` }} {...props} />
          ),
          li: ({node, ...props}) => (
            <li style={{ marginBottom: `${Math.round(4 * currentZoom)}px` }} {...props} />
          ),
          table: ({node, ...props}) => (
            <div style={{ overflowX: 'auto', margin: `${Math.round(10 * currentZoom)}px 0` }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: `${Math.round(12.5 * currentZoom)}px` }} {...props} />
            </div>
          ),
          th: ({node, ...props}) => (
            <th style={{ border: '1px solid var(--wb-border-subtle)', padding: `${Math.round(6 * currentZoom)}px ${Math.round(10 * currentZoom)}px`, background: 'var(--wb-bg-subtle)', textAlign: 'left', fontWeight: 600, color: 'var(--wb-text-bright)' }} {...props} />
          ),
          td: ({node, ...props}) => (
            <td style={{ border: '1px solid var(--wb-border-subtle)', padding: `${Math.round(6 * currentZoom)}px ${Math.round(10 * currentZoom)}px` }} {...props} />
          ),
          blockquote: ({node, ...props}) => (
            <blockquote style={{ borderLeft: '3px solid var(--wb-accent-subtle)', paddingLeft: '12px', margin: `${Math.round(10 * currentZoom)}px 0`, color: 'var(--wb-text-sub)', fontStyle: 'normal' }} {...props} />
          )
        }}
      >
        {markdownText || ''}
      </ReactMarkdown>
    </div>
  );

  const handleLoadFileToEditor = (file) => {
    onSelectCodeFile(file);
    setExportSuccessToast(`🚀 已将 [${file.name}] 载入右侧编辑器，按 ⌘↵ 可立即运行沙箱调试！`);
    setTimeout(() => setExportSuccessToast(null), 3500);
  };

  const renderCodeFilesSection = (isZen = false) => {
    if (!codeFiles || codeFiles.length === 0) return null;

    const filteredFiles = codeFiles.filter(f => {
      if (!codeSearchQuery.trim()) return true;
      const q = codeSearchQuery.toLowerCase();
      return (f.name && f.name.toLowerCase().includes(q)) || (f.doc && f.doc.toLowerCase().includes(q));
    });

    return (
      <div style={{
        marginBottom: '16px',
        background: 'var(--wb-bg-panel)',
        border: '1px solid var(--wb-border-subtle)',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.12)'
      }}>
        {/* 头部标题与折叠开关 */}
        <div 
          style={{
            padding: '9px 12px',
            background: 'var(--wb-bg-header)',
            borderBottom: isFilesDrawerExpanded ? '1px solid var(--wb-border-subtle)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            userSelect: 'none'
          }}
          onClick={() => setIsFilesDrawerExpanded(prev => !prev)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileCode size={15} color="var(--wb-accent-primary)" />
            <span style={{ fontSize: '12.5px', fontWeight: 650, color: 'var(--wb-text-bright)' }}>
              📁 本章实战源码与执行脚本库
            </span>
            <span style={{
              background: 'rgba(99, 102, 241, 0.12)',
              color: 'var(--wb-accent-primary)',
              fontSize: '11px',
              padding: '1px 6px',
              borderRadius: '8px',
              fontWeight: 600,
              fontFamily: 'var(--wb-font-mono)'
            }}>
              {codeFiles.length} 个文件
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>
              {isFilesDrawerExpanded ? '收起列表' : '展开选择并载入'}
            </span>
            <ChevronDown 
              size={14} 
              style={{ 
                transform: isFilesDrawerExpanded ? 'rotate(180deg)' : 'none',
                transition: 'transform 0.2s ease',
                color: 'var(--wb-text-dim)'
              }} 
            />
          </div>
        </div>

        {isFilesDrawerExpanded && (
          <div style={{ padding: '10px 12px', background: 'var(--wb-bg-subtle)' }}>
            {/* 搜索与提示栏 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '10px',
              background: 'var(--wb-bg-root)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '6px',
              padding: '4px 8px'
            }}>
              <Search size={12} color="var(--wb-text-dim)" />
              <input 
                type="text"
                placeholder="快速检索当前实战脚本 (如 01, attention, triton, residual)..."
                value={codeSearchQuery}
                onChange={(e) => setCodeSearchQuery(e.target.value)}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--wb-text-bright)',
                  fontSize: '11.5px',
                  fontFamily: 'inherit'
                }}
              />
              {codeSearchQuery && (
                <button 
                  onClick={() => setCodeSearchQuery('')}
                  style={{ background: 'transparent', border: 'none', color: 'var(--wb-text-dim)', cursor: 'pointer', padding: 0 }}
                >
                  <X size={12} />
                </button>
              )}
            </div>

            {/* 文件卡片滚动列表 */}
            <div 
              style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '7px', 
                maxHeight: isZen ? '340px' : '230px', 
                overflowY: 'auto' 
              }} 
              className="wb-custom-scroll"
            >
              {filteredFiles.length === 0 ? (
                <div style={{ padding: '16px', textAlign: 'center', color: 'var(--wb-text-dim)', fontSize: '11.5px' }}>
                  未找到匹配 "{codeSearchQuery}" 的脚本文件
                </div>
              ) : (
                filteredFiles.map((file, idx) => {
                  const isActive = activeCodeFile?.name === file.name;
                  const isPreviewing = expandedPreviewFile === file.name;
                  const isSolution = file.name === 'solution.py';
                  const isStarter = file.name === 'starter.py';

                  return (
                    <div 
                      key={file.name || idx}
                      style={{
                        background: isActive ? 'rgba(99, 102, 241, 0.08)' : 'var(--wb-bg-panel)',
                        border: isActive ? '1px solid var(--wb-accent-primary)' : '1px solid var(--wb-border-subtle)',
                        borderRadius: '6px',
                        padding: '7px 9px',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flex: 1 }}>
                          <FileCode size={13} color={isActive ? 'var(--wb-accent-primary)' : 'var(--wb-text-sub)'} style={{ flexShrink: 0 }} />
                          <span style={{
                            fontFamily: 'var(--wb-font-mono)',
                            fontSize: '11.5px',
                            fontWeight: 600,
                            color: isActive ? 'var(--wb-accent-primary)' : 'var(--wb-text-bright)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {file.name}
                          </span>
                          {isSolution && (
                            <span style={{ fontSize: '10px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(16, 185, 129, 0.12)', color: 'var(--wb-accent-success)', border: '1px solid rgba(16, 185, 129, 0.25)', flexShrink: 0 }}>
                              通关解
                            </span>
                          )}
                          {isStarter && (
                            <span style={{ fontSize: '10px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(245, 158, 11, 0.12)', color: 'var(--wb-accent-amber)', border: '1px solid rgba(245, 158, 11, 0.25)', flexShrink: 0 }}>
                              起手模板
                            </span>
                          )}
                          {isActive && (
                            <span style={{ fontSize: '10px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--wb-accent-primary)', border: '1px solid var(--wb-accent-primary)', flexShrink: 0, fontWeight: 600 }}>
                              🟢 正在调试
                            </span>
                          )}
                        </div>

                        {/* 操作按钮区 */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
                          <button
                            onClick={() => setExpandedPreviewFile(isPreviewing ? null : file.name)}
                            className="wb-btn-ghost"
                            style={{
                              fontSize: '11px',
                              padding: '2px 6px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '3px',
                              color: isPreviewing ? 'var(--wb-accent-primary)' : 'var(--wb-text-sub)'
                            }}
                            title={isPreviewing ? '收起源码' : '原地预览源码'}
                          >
                            <Eye size={11} />
                            <span>{isPreviewing ? '收起' : '预览'}</span>
                          </button>

                          <button
                            onClick={() => handleLoadFileToEditor(file)}
                            style={{
                              fontSize: '11px',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: isActive ? 'var(--wb-accent-primary)' : 'rgba(99, 102, 241, 0.12)',
                              color: isActive ? '#fff' : 'var(--wb-accent-primary)',
                              border: '1px solid var(--wb-accent-primary)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontWeight: 600,
                              transition: 'all 0.15s ease'
                            }}
                            title="将此文件内容载入右侧代码编辑器，可直接按 ⌘↵ 运行测试"
                          >
                            <Play size={10} fill={isActive ? '#fff' : 'currentColor'} />
                            <span>{isActive ? '重载' : '载入调试'}</span>
                          </button>
                        </div>
                      </div>

                      {/* 文件描述 */}
                      {file.doc && (
                        <div style={{
                          marginTop: '4px',
                          fontSize: '11px',
                          color: 'var(--wb-text-sub)',
                          lineHeight: '1.4',
                          paddingLeft: '19px'
                        }}>
                          💡 {file.doc}
                        </div>
                      )}

                      {/* 原地展开预览源码 */}
                      {isPreviewing && (
                        <div style={{
                          marginTop: '6px',
                          background: 'var(--wb-bg-root)',
                          border: '1px solid var(--wb-border-subtle)',
                          borderRadius: '5px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            padding: '3px 8px',
                            background: 'var(--wb-bg-header)',
                            borderBottom: '1px solid var(--wb-border-subtle)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '10.5px'
                          }}>
                            <span style={{ color: 'var(--wb-text-dim)', fontFamily: 'var(--wb-font-mono)' }}>
                              {file.name} ({Math.round((file.size || 0) / 1024 * 10) / 10} KB)
                            </span>
                            <div style={{ display: 'flex', gap: '5px' }}>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(file.content || '');
                                  setCopiedFile(file.name);
                                  setTimeout(() => setCopiedFile(null), 1500);
                                }}
                                className="wb-btn-ghost"
                                style={{ fontSize: '10px', padding: '1px 5px', display: 'flex', alignItems: 'center', gap: '3px' }}
                              >
                                {copiedFile === file.name ? <Check size={10} color="var(--wb-accent-success)" /> : <Copy size={10} />}
                                <span>{copiedFile === file.name ? '已复制' : '复制'}</span>
                              </button>
                              <button
                                onClick={() => handleLoadFileToEditor(file)}
                                className="wb-btn-ghost"
                                style={{ fontSize: '10px', padding: '1px 5px', color: 'var(--wb-accent-primary)', display: 'flex', alignItems: 'center', gap: '3px' }}
                              >
                                <Play size={10} />
                                <span>载入运行</span>
                              </button>
                            </div>
                          </div>
                          <pre style={{
                            margin: 0,
                            padding: '6px 10px',
                            maxHeight: '180px',
                            overflowY: 'auto',
                            fontFamily: 'var(--wb-font-mono)',
                            fontSize: '11px',
                            lineHeight: '1.45',
                            color: 'var(--wb-text-bright)'
                          }} className="wb-custom-scroll">
                            <code>{file.content || '# 暂无内容'}</code>
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <section className={`wb-guide-pane ${isCollapsed ? 'collapsed' : ''}`}>
      {/* 顶部标签切换栏 */}
      <div style={{
        height: '42px',
        padding: '0 10px',
        borderBottom: '1px solid var(--wb-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--wb-bg-header)'
      }}>
        {/* Tab 切换组 */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={() => setActiveTab('mission')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: activeTab === 'mission' ? 'var(--wb-bg-subtle)' : 'transparent',
              border: activeTab === 'mission' ? '1px solid var(--wb-border-subtle)' : '1px solid transparent',
              color: activeTab === 'mission' ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)',
              padding: '4px 8px',
              borderRadius: '5px',
              fontSize: '11.5px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <Target size={13} color={activeTab === 'mission' ? 'var(--wb-accent-subtle)' : 'currentColor'} />
            <span>🎯 闯关实战</span>
          </button>

          <button
            onClick={() => setActiveTab('doc')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: activeTab === 'doc' ? 'var(--wb-bg-subtle)' : 'transparent',
              border: activeTab === 'doc' ? '1px solid var(--wb-border-subtle)' : '1px solid transparent',
              color: activeTab === 'doc' ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)',
              padding: '4px 8px',
              borderRadius: '5px',
              fontSize: '11.5px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <BookOpen size={13} color={activeTab === 'doc' ? 'var(--wb-accent-primary)' : 'currentColor'} />
            <span>📖 知识手册</span>
          </button>
        </div>

        {/* 右侧动作组 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative' }}>
          {/* 在手册模式下展示放大缩小与沉浸控制 */}
          {activeTab === 'doc' && renderZoomControls(false)}

          {/* 导出讲义按钮与下拉卡片 */}
          <div ref={exportMenuRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setShowExportMenu(prev => !prev)}
              className="wb-btn-ghost"
              style={{
                fontSize: '11px',
                padding: '2px 7px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: showExportMenu ? 'var(--wb-bg-hover)' : undefined
              }}
              title="导出当前关卡完整实战讲义与参考代码"
            >
              <Download size={12} />
              <span>导出讲义</span>
              <ChevronDown size={10} />
            </button>

            {/* 导出选项下拉卡片 */}
            {showExportMenu && (
              <div style={{
                position: 'absolute',
                top: '28px',
                right: 0,
                width: '180px',
                background: 'var(--wb-bg-panel)',
                border: '1px solid var(--wb-border-active)',
                borderRadius: '8px',
                padding: '4px',
                boxShadow: '0 12px 30px rgba(0,0,0,0.5)',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                animation: 'fadeIn 0.15s ease'
              }}>
                <button
                  onClick={() => handleExportMarkdown(mission)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    padding: '6px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '11.5px',
                    color: 'var(--wb-text-bright)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--wb-bg-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <FileText size={13} color="var(--wb-accent-subtle)" />
                  <span>导出 Markdown (.md)</span>
                </button>

                <button
                  onClick={handlePrintHandbook}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '5px',
                    padding: '6px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '11.5px',
                    color: 'var(--wb-text-bright)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--wb-bg-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Printer size={13} color="var(--wb-accent-amber)" />
                  <span>打印 / 另存为 PDF</span>
                </button>
              </div>
            )}
          </div>

          {phaseDetail.starter_code && (
            <button
              onClick={() => onLoadStarterCode(phaseDetail.starter_code)}
              className="wb-btn-ghost"
              style={{ fontSize: '11px', padding: '2px 6px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="载入官方闯关代码模板"
            >
              <FileCode size={12} />
              <span>载入模板</span>
            </button>
          )}

          <button
            onClick={onToggleCollapse}
            className="wb-btn-ghost"
            style={{ padding: '4px' }}
            title="收起侧栏专注编码"
          >
            <ChevronLeft size={14} />
          </button>
        </div>
      </div>

      {/* 导出成功 Toast */}
      {exportSuccessToast && (
        <div style={{
          position: 'absolute',
          top: '48px',
          right: '12px',
          zIndex: 100,
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-accent-success)',
          borderRadius: '6px',
          padding: '6px 12px',
          fontSize: '11.5px',
          color: 'var(--wb-text-bright)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          animation: 'fadeIn 0.15s ease'
        }}>
          <Check size={12} color="var(--wb-accent-success)" />
          <span>{exportSuccessToast}</span>
        </div>
      )}

      {/* 滚动内容区 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }} className="wb-custom-scroll">
        
        {/* ================= Tab 1: 🎯 闯关挑战模式 ================= */}
        {activeTab === 'mission' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* 1. 关卡挑战目标卡片 */}
            <div style={{
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '8px',
              padding: '14px 16px',
              borderLeft: '4px solid var(--wb-accent-subtle)'
            }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--wb-accent-subtle)', textTransform: 'uppercase', marginBottom: '4px' }}>
                MISSION CHALLENGE
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--wb-text-bright)', marginBottom: '6px' }}>
                {mission.mission_title}
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--wb-text-sub)', lineHeight: '1.5' }}>
                {mission.mission_goal}
              </div>
            </div>

            {/* 2. 具体学习与闯关四步方法论 (清晰说明如何学习与通关) */}
            <div style={{
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '8px',
              padding: '14px 16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                <ListOrdered size={15} color="var(--wb-accent-primary)" />
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                  学习与闯关标准四步法
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {mission.learning_steps?.map((step, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '12px',
                    color: 'var(--wb-text-normal)',
                    lineHeight: '1.5'
                  }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: 'var(--wb-bg-hover)',
                      fontSize: '10.5px',
                      fontWeight: 700,
                      color: 'var(--wb-accent-subtle)',
                      flexShrink: 0,
                      marginTop: '2px'
                    }}>
                      {idx + 1}
                    </span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. 核心代码实现要求 */}
            <div style={{
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '8px',
              padding: '14px 16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                <Code2 size={15} color="var(--wb-accent-success)" />
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                  核心编码要求与接口规范
                </span>
              </div>

              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--wb-text-sub)', lineHeight: '1.6' }}>
                {mission.requirements?.map((req, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {req}
                  </li>
                ))}
              </ul>
            </div>

            {/* 4. 自动化评测验收标准 */}
            <div style={{
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '8px',
              padding: '14px 16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                <ShieldCheck size={15} color="var(--wb-accent-subtle)" />
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                  评测验收通过标准
                </span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--wb-text-dim)', lineHeight: '1.5' }}>
                {mission.acceptance_criteria}
              </div>
            </div>

            {/* 5. 启发式思路 Hint */}
            {mission.hint && (
              <div style={{
                background: 'var(--wb-bg-panel)',
                border: '1px dashed var(--wb-border-subtle)',
                borderRadius: '8px',
                padding: '12px 14px'
              }}>
                <div 
                  onClick={() => setIsHintExpanded(!isHintExpanded)}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Lightbulb size={14} color="#f59e0b" />
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#f59e0b' }}>
                      💡 遇到卡点？点击查看启发式解题思路
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>
                    {isHintExpanded ? '收起' : '展开'}
                  </span>
                </div>
                {isHintExpanded && (
                  <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--wb-text-sub)', lineHeight: '1.5', borderTop: '1px solid var(--wb-border-subtle)', paddingTop: '8px' }}>
                    {mission.hint}
                  </div>
                )}
              </div>
            )}

            {/* 6. 验证自检目标 Checklist */}
            {checklist.length > 0 && (
              <div style={{
                background: 'var(--wb-bg-subtle)',
                border: '1px solid var(--wb-border-subtle)',
                borderRadius: '8px',
                padding: '12px 14px'
              }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--wb-text-dim)', marginBottom: '8px', textTransform: 'uppercase' }}>
                  通关自检清单
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {checklist.map((item, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => toggleCheck(idx)}
                      style={{ 
                        display: 'flex', 
                        alignItems: 'flex-start', 
                        gap: '8px', 
                        cursor: 'pointer',
                        fontSize: '12px',
                        color: item.done ? 'var(--wb-text-dim)' : 'var(--wb-text-bright)',
                        textDecoration: item.done ? 'line-through' : 'none',
                        lineHeight: '1.4'
                      }}
                    >
                      <div style={{ marginTop: '2px' }}>
                        {item.done ? <CheckSquare size={13} color="var(--wb-accent-success)" /> : <Square size={13} color="var(--wb-text-dim)" />}
                      </div>
                      <span>{item.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================= Tab 2: 📖 知识手册模式 ================= */}
        {activeTab === 'doc' && (
          <div>
            {renderCodeFilesSection(false)}
            {renderMarkdownContent(phaseDetail.guide_markdown || '', docZoom)}
          </div>
        )}

      </div>
    </section>

    {/* ================= 沉浸式宽屏/全屏大弹窗研读模式 (Zen Mode Modal) ================= */}
    {isZenMode && (
      <div 
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 99999,
          background: 'rgba(7, 10, 15, 0.84)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          animation: 'fadeIn 0.15s ease'
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) setIsZenMode(false);
        }}
      >
        <div style={{
          width: '100%',
          maxWidth: '980px',
          height: '92vh',
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-border-active)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 70px rgba(0, 0, 0, 0.65)',
          overflow: 'hidden'
        }}>
          {/* 弹窗顶部导航栏 */}
          <div style={{
            height: '50px',
            padding: '0 20px',
            borderBottom: '1px solid var(--wb-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--wb-bg-header)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{
                background: 'rgba(99, 102, 241, 0.12)',
                color: 'var(--wb-accent-primary)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                fontFamily: 'var(--wb-font-mono)'
              }}>
                {phaseDetail.id || 'DOC'}
              </span>
              <span style={{ fontSize: '14px', fontWeight: 650, color: 'var(--wb-text-bright)' }}>
                {phaseDetail.title || activePhaseTitle || '知识手册'}
              </span>
              <span style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)' }}>
                · 沉浸式宽屏研读
              </span>
            </div>

            {/* 弹窗右侧动作组 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* 弹窗内的缩放控制器 */}
              {renderZoomControls(true)}

              <button
                onClick={() => handleExportMarkdown(mission)}
                className="wb-btn-ghost"
                style={{ fontSize: '12px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '5px' }}
                title="导出完整讲义为 Markdown 文件"
              >
                <FileText size={13} color="var(--wb-accent-subtle)" />
                <span>导出</span>
              </button>

              <button
                onClick={handlePrintHandbook}
                className="wb-btn-ghost"
                style={{ fontSize: '12px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '5px' }}
                title="打印讲义或另存为 PDF"
              >
                <Printer size={13} color="var(--wb-accent-amber)" />
                <span>打印/PDF</span>
              </button>

              <button
                onClick={() => setIsZenMode(false)}
                className="wb-btn-ghost"
                style={{
                  padding: '5px',
                  borderRadius: '6px',
                  color: 'var(--wb-text-sub)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title="退出沉浸模式 (ESC)"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* 弹窗大内容滚动区 */}
          <div 
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '32px 48px',
              background: 'var(--wb-bg-root)'
            }}
            className="wb-custom-scroll"
          >
            <div style={{ maxWidth: '840px', margin: '0 auto' }}>
              {renderCodeFilesSection(true)}
              {renderMarkdownContent(phaseDetail.guide_markdown || '', docZoom)}
            </div>
          </div>

          {/* 弹窗底部信息栏 */}
          <div style={{
            height: '32px',
            padding: '0 20px',
            borderTop: '1px solid var(--wb-border-subtle)',
            background: 'var(--wb-bg-header)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--wb-text-dim)'
          }}>
            <span>💡 提示：支持按 <code>ESC</code> 键随时退出沉浸视图，缩放比例已自动持久化保存</span>
            <span>当前字号比例：{Math.round(docZoom * 100)}%</span>
          </div>
        </div>
      </div>
    )}
  </>
  );
}
