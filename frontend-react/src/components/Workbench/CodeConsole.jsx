import React, { useState, useEffect, useRef } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import { 
  Play, CheckCircle, RotateCcw, Copy, Terminal, 
  Sparkles, CheckCircle2, XCircle, Clock, ChevronDown, ChevronUp,
  Maximize2, Minimize2, GripHorizontal, Award, RefreshCw, Send,
  ShieldCheck, AlertTriangle, Lightbulb, Save, Undo2, AlertCircle, X,
  GitCompare, ArrowRight, BookOpen, Lock, Unlock, Building2, Zap, Image, Eye,
  Search, FileCode, Check, Code2, Trash2, Filter
} from 'lucide-react';
import { PYTHON_METHODS_CATALOG, getPythonCompletionItems, getPythonHoverInfo } from './pythonCompletionData';

export default function CodeConsole({
  phaseId = '',
  starterCode = '',
  solutionCode = '',
  solutionSource = '',
  solutionDoc = '',
  starterSource = '',
  passedHistory = null,
  testCode = '',
  currentTheme = 'obsidian',
  phases = [],
  codeFiles = [],
  activeCodeFile = null,
  onSelectCodeFile = () => {},
  currentTenant = null,
  currentUser = null,
  onUpdateTenantQuota = () => {},
  isChallengeMode = true,
  isUnlocked = true,
  onPassPhase = () => {},
  onNavigatePhase = () => {},
  onToggleChallengeMode = () => {}
}) {
  const [code, setCode] = useState(starterCode);
  const [activeTab, setActiveTab] = useState('terminal'); // 'terminal' | 'test' | 'mentor'
  const [isRunning, setIsRunning] = useState(false);

  // 草稿箱与持久化状态体系 (Phase 2A)
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved'
  const [draftUpdatedAt, setDraftUpdatedAt] = useState(null);
  const [hasDraft, setHasDraft] = useState(false);
  const [draftBackup, setDraftBackup] = useState(null);
  const [showResetModal, setShowResetModal] = useState(false);
  const [toast, setToast] = useState(null); // { message: string, undoAction?: () => void }

  // 代码审查 Diff 对比体系 (Phase 2B 升级：具备明确代码出处与多基准溯源)
  const [isDiffMode, setIsDiffMode] = useState(false);
  // 对比基准来源: 'solution' (官方生产级标准实现) | 'passed' (历史成功通关快照) | 'starter' (官方起手模板)
  const [diffBaseSource, setDiffBaseSource] = useState('solution');
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successStats, setSuccessStats] = useState(null);

  // 多代码文件快速切换与下拉筛选
  const [showFilePickerDropdown, setShowFilePickerDropdown] = useState(false);
  const [fileSearchQuery, setFileSearchQuery] = useState('');
  const filePickerRef = useRef(null);
  const [showVerifyExternalConfirmModal, setShowVerifyExternalConfirmModal] = useState(false);

  const debounceTimerRef = useRef(null);
  const toastTimeoutRef = useRef(null);
  const lastStarterCodeRef = useRef(starterCode);
  const isInitialMountRef = useRef(true);

  // 终端高度记忆与伸缩控制体系
  const containerRef = useRef(null);
  const [terminalHeight, setTerminalHeight] = useState(() => {
    try {
      const saved = localStorage.getItem('wb_terminal_height');
      return saved ? Math.max(120, Math.min(parseInt(saved, 10), 900)) : 260;
    } catch {
      return 260;
    }
  }); // 记忆高度
  const [isTerminalCollapsed, setIsTerminalCollapsed] = useState(false);
  const [isTerminalMaximized, setIsTerminalMaximized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const isDraggingRef = useRef(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(terminalHeight);

  const [runResult, setRunResult] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [mentorReview, setMentorReview] = useState(null);
  const [isMentorLoading, setIsMentorLoading] = useState(false);
  const [isMentorStreaming, setIsMentorStreaming] = useState(false);
  const [mentorQuestion, setMentorQuestion] = useState('');
  const [mentorImage, setMentorImage] = useState(null); // Base64 编码图片
  const [suspiciousLines, setSuspiciousLines] = useState([]); // 错误调用栈定位行
  const [highlightLine, setHighlightLine] = useState(null);
  const [copied, setCopied] = useState(false);
  const mentorAbortRef = useRef(null);
  const editorInstanceRef = useRef(null);

  // 代码方法自动快捷提醒与速查助手体系
  const [showMethodAssistDrawer, setShowMethodAssistDrawer] = useState(false);
  const [searchMethodQuery, setSearchMethodQuery] = useState('');
  const [selectedMethodCategory, setSelectedMethodCategory] = useState('ALL');
  const [insertedMethodName, setInsertedMethodName] = useState(null);
  const completionDisposableRef = useRef(null);
  const hoverDisposableRef = useRef(null);

  // 控制台输出过滤与检索体系
  const [consoleFilter, setConsoleFilter] = useState('all'); // 'all' | 'stdout' | 'stderr'
  const [consoleSearchQuery, setConsoleSearchQuery] = useState('');

  // 划词定向提问与多轮对话体系
  const [selectedCode, setSelectedCode] = useState('');
  const [selectionWidgetPos, setSelectionWidgetPos] = useState(null); // { top, left }
  const [mentorChatHistory, setMentorChatHistory] = useState([]); // [{ role: 'user'|'assistant', content: '...' }]

  // 引用最新函数指针，供 Monaco 编辑器快捷键无缝调用
  const handleRunCodeRef = useRef(null);
  const handleSaveImmediatelyRef = useRef(null);

  // Monaco 编辑器挂载与智能代码方法提醒注册
  const handleEditorMount = (editor, monaco) => {
    editorInstanceRef.current = editor;

    // 清理可能遗留的旧 provider
    if (completionDisposableRef.current) {
      completionDisposableRef.current.dispose();
      completionDisposableRef.current = null;
    }
    if (hoverDisposableRef.current) {
      hoverDisposableRef.current.dispose();
      hoverDisposableRef.current = null;
    }

    try {
      // 注册 Monaco 编辑器内原生快捷键：⌘Enter / Ctrl+Enter 运行代码，⌘S / Ctrl+S 暂存草稿
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        if (handleRunCodeRef.current) {
          handleRunCodeRef.current();
        }
      });
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        if (handleSaveImmediatelyRef.current) {
          handleSaveImmediatelyRef.current();
        }
      });

      // 1. 注册 Python 智能代码方法自动补全 Provider (全面支持 os. 等点号级命名空间精准联想)
      completionDisposableRef.current = monaco.languages.registerCompletionItemProvider('python', {
        triggerCharacters: ['.', '(', ' ', '_', '"', "'"],
        provideCompletionItems: (model, position) => {
          const lineContent = model.getLineContent(position.lineNumber);
          const lineUntilPosition = lineContent.substring(0, position.column - 1);
          const word = model.getWordUntilPosition(position);
          const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endColumn: word.endColumn
          };
          const suggestions = getPythonCompletionItems(monaco, range, lineUntilPosition);
          return { suggestions };
        }
      });

      // 2. 注册 Python 代码方法鼠标悬浮文档 Provider
      hoverDisposableRef.current = monaco.languages.registerHoverProvider('python', {
        provideHover: (model, position) => {
          const lineContent = model.getLineContent(position.lineNumber);
          const word = model.getWordAtPosition(position);
          if (!word) return null;
          return getPythonHoverInfo(monaco, word.word, lineContent);
        }
      });

      // 3. 监听编辑器划词选区，呼出定向提问悬浮药丸
      editor.onDidChangeCursorSelection((e) => {
        const selection = e.selection;
        if (!selection || selection.isEmpty()) {
          setSelectionWidgetPos(null);
          setSelectedCode('');
          return;
        }
        const model = editor.getModel();
        if (!model) return;
        const text = model.getValueInRange(selection);
        if (text && text.trim().length > 0) {
          const endPos = selection.getEndPosition();
          const scrolledPos = editor.getScrolledVisiblePosition(endPos);
          if (scrolledPos) {
            setSelectedCode(text);
            setSelectionWidgetPos({
              top: Math.max(10, scrolledPos.top - 32),
              left: Math.max(10, scrolledPos.left + 15)
            });
          }
        } else {
          setSelectionWidgetPos(null);
          setSelectedCode('');
        }
      });
    } catch (e) {
      console.warn('Monaco completion provider registration notice:', e);
    }
  };

  // 一键将 AI 导师诊断报告中的推荐代码替换/回填到当前编辑器
  const handleApplyMentorSnippet = (snippet) => {
    if (!snippet || !snippet.trim()) return;
    const cleanSnippet = snippet.trim();
    // 自动备份当前草稿
    try {
      localStorage.setItem(`ai_learning_draft_backup_${phaseId}`, JSON.stringify({
        code: code,
        updatedAt: Date.now()
      }));
    } catch {}
    handleCodeChange(cleanSnippet);
    showToast('🚀 已将 AI 导师推荐代码应用到编辑区', () => handleRestoreBackup(code));
  };

  // 一键将标准代码方法模版注入编辑器光标处
  const handleInsertMethod = (item) => {
    if (!editorInstanceRef.current) return;
    const editor = editorInstanceRef.current;
    const position = editor.getPosition() || { lineNumber: 1, column: 1 };
    
    // 剔除 snippet 变量占位符，转换为纯净可用代码
    const cleanCode = item.snippet.replace(/\$\{\d+:?([^}]*)\}/g, '$1').replace(/\$0/g, '');
    
    const range = {
      startLineNumber: position.lineNumber,
      startColumn: position.column,
      endLineNumber: position.lineNumber,
      endColumn: position.column
    };

    editor.executeEdits('insert-method-snippet', [
      {
        range: range,
        text: cleanCode,
        forceMoveMarkers: true
      }
    ]);
    editor.focus();
    setInsertedMethodName(item.name);
    setTimeout(() => setInsertedMethodName(null), 2200);
  };

  // 组件卸载时释放 Monaco providers
  useEffect(() => {
    return () => {
      if (completionDisposableRef.current) completionDisposableRef.current.dispose();
      if (hoverDisposableRef.current) hoverDisposableRef.current.dispose();
    };
  }, []);

  // 鼠标拖拽调节高度逻辑 (上下均可自由拖拽)
  const handleMouseDownResize = (e) => {
    e.preventDefault();
    e.stopPropagation();
    isDraggingRef.current = true;
    setIsDragging(true);
    startYRef.current = e.clientY;
    startHeightRef.current = isTerminalCollapsed ? 34 : terminalHeight;

    const onMouseMove = (moveEvent) => {
      if (!isDraggingRef.current) return;
      // 往上拖 deltaY 为正 (startY > clientY)，高度增加；往下拖 deltaY 为负，高度减小
      const deltaY = startYRef.current - moveEvent.clientY;
      const nextHeight = startHeightRef.current + deltaY;

      if (nextHeight < 60) {
        setIsTerminalCollapsed(true);
      } else {
        setIsTerminalCollapsed(false);
        setIsTerminalMaximized(false);
        
        // 动态获取外层工作区高度，确保上方代码区至少留有 90px 可视空间
        const totalHeight = containerRef.current?.clientHeight || window.innerHeight;
        const maxHeight = Math.max(200, totalHeight - 90);
        const clamped = Math.min(Math.max(100, nextHeight), maxHeight);
        
        setTerminalHeight(clamped);
        try {
          localStorage.setItem('wb_terminal_height', clamped.toString());
        } catch {}
      }
    };

    const onMouseUp = () => {
      isDraggingRef.current = false;
      setIsDragging(false);
      window.removeEventListener('mousemove', onMouseMove, true);
      window.removeEventListener('mouseup', onMouseUp, true);
    };

    window.addEventListener('mousemove', onMouseMove, true);
    window.addEventListener('mouseup', onMouseUp, true);
  };

  // 折叠/恢复
  const toggleCollapse = () => {
    if (isTerminalCollapsed) {
      setIsTerminalCollapsed(false);
    } else {
      setIsTerminalCollapsed(true);
      setIsTerminalMaximized(false);
    }
  };

  // 最大化/还原
  const toggleMaximize = () => {
    if (isTerminalMaximized) {
      setIsTerminalMaximized(false);
    } else {
      setIsTerminalCollapsed(false);
      setIsTerminalMaximized(true);
    }
  };

  // 格式化时间辅助函数
  const formatDraftTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  };

  // Toast 轻提示
  const showToast = (message, undoAction = null, duration = 3600) => {
    setToast({ message, undoAction });
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => {
      setToast(null);
    }, duration);
  };

  // 1. 当关卡 phaseId 改变时：优先加载本地草稿，杜绝进度丢失
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    let loadedCode = starterCode;
    let draftFound = false;
    let draftTime = null;

    try {
      const saved = localStorage.getItem(`ai_learning_draft_${phaseId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && typeof parsed.code === 'string' && parsed.code.trim().length > 0) {
          loadedCode = parsed.code;
          draftFound = true;
          draftTime = parsed.updatedAt;
        }
      }

      const backup = localStorage.getItem(`ai_learning_draft_backup_${phaseId}`);
      if (backup) {
        const parsedBackup = JSON.parse(backup);
        setDraftBackup(parsedBackup.code);
      } else {
        setDraftBackup(null);
      }
    } catch (e) {
      console.warn('Load draft failed:', e);
    }

    setCode(loadedCode);
    setHasDraft(draftFound);
    setDraftUpdatedAt(draftTime);
    setSaveStatus(draftFound ? 'saved' : 'idle');
    setRunResult(null);
    setVerifyResult(null);
    setMentorReview(null);
    setIsDiffMode(false);
    setShowSuccessModal(false);

    if (draftFound && !isInitialMountRef.current) {
      showToast(`已恢复本地草稿 (${formatDraftTime(draftTime)})`);
    }
    isInitialMountRef.current = false;
    lastStarterCodeRef.current = starterCode;
  }, [phaseId]);

  // 点击外部收起文件选择器
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (filePickerRef.current && !filePickerRef.current.contains(e.target)) {
        setShowFilePickerDropdown(false);
      }
    };
    if (showFilePickerDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showFilePickerDropdown]);

  // 2. 当配套实战脚本 activeCodeFile 变化时：载入其内容至编辑器
  useEffect(() => {
    if (activeCodeFile) {
      setCode(activeCodeFile.content || '');
      setIsDiffMode(false);
      setRunResult(null);
      showToast(`📁 已载入脚本: ${activeCodeFile.name}`);
    } else {
      // 恢复主通关代码（从草稿箱或 starterCode）
      try {
        const saved = localStorage.getItem(`ai_learning_draft_${phaseId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && typeof parsed.code === 'string' && parsed.code.trim().length > 0) {
            setCode(parsed.code);
            return;
          }
        }
        setCode(starterCode);
      } catch {
        setCode(starterCode);
      }
    }
  }, [activeCodeFile]);

  // 3. 当 starterCode 异步到达时：若当前 code 为空或无有效草稿，安全同步初始代码
  useEffect(() => {
    if (activeCodeFile) return;
    if (starterCode) {
      lastStarterCodeRef.current = starterCode;
      try {
        const saved = localStorage.getItem(`ai_learning_draft_${phaseId}`);
        let validDraft = false;
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && typeof parsed.code === 'string' && parsed.code.trim().length > 0) {
            validDraft = true;
          }
        }
        if (!validDraft || !code || !code.trim()) {
          setCode(starterCode);
        }
      } catch {
        if (!code || !code.trim()) {
          setCode(starterCode);
        }
      }
    }
  }, [starterCode, phaseId, activeCodeFile]);

  // 4. 用户在编辑器中输入：防抖自动暂存到 localStorage (仅主通关代码保存草稿，防止污染)
  const handleCodeChange = (newVal) => {
    const val = newVal || '';
    setCode(val);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (activeCodeFile) {
      setSaveStatus('saved');
      return;
    }

    setSaveStatus('saving');
    debounceTimerRef.current = setTimeout(() => {
      try {
        const now = Date.now();
        localStorage.setItem(`ai_learning_draft_${phaseId}`, JSON.stringify({
          code: val,
          updatedAt: now,
          phaseId
        }));
        setDraftUpdatedAt(now);
        setHasDraft(true);
        setSaveStatus('saved');
      } catch (e) {
        console.warn('Auto save draft failed:', e);
      }
    }, 700);
  };

  // 4. 立即手动保存草稿
  const handleSaveImmediately = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    try {
      const now = Date.now();
      localStorage.setItem(`ai_learning_draft_${phaseId}`, JSON.stringify({
        code,
        updatedAt: now,
        phaseId
      }));
      setDraftUpdatedAt(now);
      setHasDraft(true);
      setSaveStatus('saved');
      showToast('✔ 草稿已即时保存 (⌘S)');
    } catch (e) {
      showToast(`⚠️ 保存失败: ${e.message}`);
    }
  };

  // 5. 重置初始代码弹窗确认
  const handleResetClick = () => {
    if (code === starterCode && !hasDraft) {
      showToast('当前已是关卡初始模板');
      return;
    }
    setShowResetModal(true);
  };

  const confirmReset = () => {
    setShowResetModal(false);
    const currentBackup = code;
    try {
      localStorage.setItem(`ai_learning_draft_backup_${phaseId}`, JSON.stringify({
        code: currentBackup,
        updatedAt: Date.now()
      }));
      localStorage.removeItem(`ai_learning_draft_${phaseId}`);
    } catch {}

    setDraftBackup(currentBackup);
    setCode(starterCode);
    setHasDraft(false);
    setDraftUpdatedAt(null);
    setSaveStatus('idle');

    showToast('已恢复为官方初始模板', () => handleRestoreBackup(currentBackup));
  };

  // 6. 撤销重置 / 恢复草稿
  const handleRestoreBackup = (codeToRestore = null) => {
    const targetCode = codeToRestore || draftBackup;
    if (!targetCode) {
      showToast('未检测到可撤销的历史草稿');
      return;
    }
    try {
      const now = Date.now();
      localStorage.setItem(`ai_learning_draft_${phaseId}`, JSON.stringify({
        code: targetCode,
        updatedAt: now,
        phaseId
      }));
      setCode(targetCode);
      setHasDraft(true);
      setDraftUpdatedAt(now);
      setSaveStatus('saved');
      showToast('✔ 已撤销重置，成功找回草稿');
    } catch (e) {
      showToast(`恢复草稿失败: ${e.message}`);
    }
  };

  // 读取历史成功通关快照代码
  const getPassedCode = () => {
    try {
      return passedHistory?.passedCode || localStorage.getItem(`ai_learning_passed_code_${phaseId}`) || '';
    } catch {
      return '';
    }
  };

  // 获取当前选定 Diff 基准的完整出处元数据与工程审查导引
  const getDiffMeta = () => {
    if (diffBaseSource === 'passed') {
      const pCode = getPassedCode();
      const passedTimeStr = passedHistory?.completedAt 
        ? new Date(passedHistory.completedAt).toLocaleString() 
        : '历史评测通过快照';
      return {
        code: pCode || starterCode,
        title: '我的历史成功通关代码快照',
        sourceName: '历史通关快照',
        sourceBadge: `历史记录 · ${passedTimeStr}`,
        sourcePath: `通关存盘 (时间: ${passedTimeStr})`,
        tagColor: '#34d399',
        tagBg: 'rgba(52, 211, 153, 0.12)',
        architectureDoc: '工程审查目的：审视本次优化/重构相较于历史通关版本的演进差异，确保不破坏已有功能基线。',
        hasContent: Boolean(pCode),
        emptyNotice: !pCode ? '当前关卡尚未提交通过评测，暂无历史通关快照' : ''
      };
    } else if (diffBaseSource === 'starter') {
      return {
        code: starterCode,
        title: '官方起手脚手架模板',
        sourceName: '官方起手模板',
        sourceBadge: '官方初始模板 · 空白骨架',
        sourcePath: starterSource || `${phaseId}/starter.py`,
        tagColor: '#60a5fa',
        tagBg: 'rgba(96, 165, 250, 0.12)',
        architectureDoc: '工程审查目的：审视从初始空模板到当前草稿的所有业务新增逻辑与增量实现。',
        hasContent: Boolean(starterCode),
        emptyNotice: ''
      };
    } else {
      // 默认: solution 官方工业级标准架构
      return {
        code: solutionCode || starterCode,
        title: '官方工业级标准参考实现',
        sourceName: '官方标准解',
        sourceBadge: '官方基准 · 生产级架构',
        sourcePath: solutionSource || `${phaseId}/solution.py (官方基准架构实现)`,
        tagColor: '#fbbf24',
        tagBg: 'rgba(245, 158, 11, 0.12)',
        architectureDoc: solutionDoc || '工程审查目的：对照官方生产级架构规范，审查参数防御校验、异常处理与完整业务流闭环。',
        hasContent: Boolean(solutionCode),
        emptyNotice: !solutionCode ? '官方暂未配置本阶段参考答案' : ''
      };
    }
  };

  // 7. 切换 Diff 代码对比模式
  const handleToggleDiff = () => {
    setIsDiffMode(prev => !prev);
  };

  // 8. 采纳选定的基准代码到当前本地工作区
  const handleAdoptSolution = () => {
    const meta = getDiffMeta();
    if (!meta.code) {
      showToast('当前基准代码为空，无法采纳');
      return;
    }
    handleCodeChange(meta.code);
    showToast(`✔ 已采纳【${meta.sourceName}】覆盖至当前工作草稿`);
  };

  // 9. 全局快捷键监听 (⌘S 即时保存, ⌘Enter 运行)
  useEffect(() => {
    handleRunCodeRef.current = handleRunCode;
    handleSaveImmediatelyRef.current = handleSaveImmediately;
  });

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSaveImmediately();
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleRunCode();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [code, phaseId, starterCode]);

  const handleRunCode = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setIsTerminalCollapsed(false);
    setActiveTab('terminal');
    setRunResult({ status: 'running', stdout: '正在分配安全隔离沙箱资源...\n', stderr: '', execution_time_ms: 0 });

    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const resp = await fetch('/api/v1/sandbox/run', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        },
        body: JSON.stringify({ code, timeout: 60 })
      });
      const data = await resp.json();
      setRunResult(data);
      if (data.tenant_quota) {
        onUpdateTenantQuota(data.tenant_quota);
      }
    } catch (err) {
      setRunResult({
        status: 'error',
        stdout: '',
        stderr: `沙箱连接失败: ${err.message}`,
        execution_time_ms: 0
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleVerify = async (overrideCode = null) => {
    if (isRunning) return;

    // 如果处于外部脚本模式，且未指定 overrideCode，弹窗引导学员
    if (activeCodeFile && !overrideCode) {
      setShowVerifyExternalConfirmModal(true);
      return;
    }

    const codeToVerify = overrideCode || code;
    setIsRunning(true);
    setIsTerminalCollapsed(false);
    setActiveTab('test');
    setVerifyResult(null);

    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const resp = await fetch('/api/v1/sandbox/verify', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        },
        body: JSON.stringify({ phase_id: phaseId, user_code: codeToVerify, timeout: 90 })
      });
      const data = await resp.json();
      setVerifyResult(data);
      if (data.tenant_quota) {
        onUpdateTenantQuota(data.tenant_quota);
      }
      if (data.passed) {
        try {
          localStorage.setItem(`ai_learning_passed_code_${phaseId}`, codeToVerify);
        } catch (e) {
          console.warn('Save passed code snapshot failed:', e);
        }
        onPassPhase(phaseId, { 
          execution_time_ms: data.details?.execution_time_ms,
          passedAt: Date.now(),
          passedCode: codeToVerify
        });

        // 触发通关卡片与下一关路线引导 (Phase 2B)
        const currentIdx = phases.findIndex(p => p.id === phaseId);
        const nextPhase = (currentIdx >= 0 && currentIdx < phases.length - 1) ? phases[currentIdx + 1] : null;
        const p = phases.find(x => x.id === phaseId);
        const xp = p ? (p.difficulty === 'Advanced' ? 240 : p.difficulty === 'Intermediate' ? 140 : 80) : 100;
        setSuccessStats({
          xp,
          timeMs: data.details?.execution_time_ms || 35,
          nextPhase,
          phaseTitle: p?.title || phaseId
        });
        setShowSuccessModal(true);
      }
    } catch (err) {
      setVerifyResult({
        passed: false,
        message: `评测失败: ${err.message}`,
        details: { total_tests: 0, passed_tests: 0, execution_time_ms: 0 }
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleConfirmSwitchToSolutionAndVerify = () => {
    setShowVerifyExternalConfirmModal(false);
    onSelectCodeFile(null); // 切回主通关解
    let targetCode = starterCode;
    try {
      const saved = localStorage.getItem(`ai_learning_draft_${phaseId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        targetCode = parsed.code || starterCode;
      }
    } catch {}
    handleVerify(targetCode);
  };

  const handleForceVerifyCurrentScript = () => {
    setShowVerifyExternalConfirmModal(false);
    handleVerify(code);
  };

  const handleAskMentor = async (overrideQ = null) => {
    // 中止先前的未完成流
    if (mentorAbortRef.current) {
      mentorAbortRef.current.abort();
    }
    const abortController = new AbortController();
    mentorAbortRef.current = abortController;

    setIsMentorLoading(true);
    setIsMentorStreaming(true);
    setIsTerminalCollapsed(false);
    setActiveTab('mentor');
    const errText = (runResult?.stderr || '') + '\n' + (verifyResult?.details?.stderr || '');
    const q = overrideQ || mentorQuestion.trim() || '请结合本关实战目标与 DFL 决策分析，给出全方位深度 Code Review 与企业级生产落地建议';

    // 初始重置诊断面板
    setMentorReview({
      status: 'loading',
      mode: (errText.trim().length > 0) ? 'troubleshooting' : 'review',
      score: 85,
      level: 'A',
      phase_title: phaseId,
      review: ''
    });

    try {
      const activeSelectedCode = selectedCode; // 保存当前选中的局部代码
      const payload = {
        phase_id: phaseId,
        user_code: code,
        selected_code: activeSelectedCode || undefined,
        chat_history: mentorChatHistory.length > 0 ? mentorChatHistory : undefined,
        error_output: errText,
        question: q,
        image_data: mentorImage
      };

      // 将本次提问推入历史记录
      setMentorChatHistory(prev => [
        ...prev,
        { role: 'user', content: activeSelectedCode ? `[关注代码]:\n\`\`\`python\n${activeSelectedCode}\n\`\`\`\n\n${q}` : q }
      ]);

      const resp = await fetch('/api/v1/mentor/review/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortController.signal,
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        throw new Error(`HTTP error ${resp.status}`);
      }

      setIsMentorLoading(false); // 收到首包流，解除纯 Loading 旋转，进入打字机流式阶段
      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedReview = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;
          const dataStr = trimmed.replace(/^data:\s*/, '');
          if (dataStr === '[DONE]') {
            setIsMentorStreaming(false);
            break;
          }
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'meta') {
              setMentorReview(prev => ({
                ...(prev || {}),
                ...parsed,
                review: accumulatedReview
              }));
              if (parsed.suspicious_lines?.length) {
                setSuspiciousLines(parsed.suspicious_lines);
                // 自动高亮首个嫌疑行
                jumpToLine(parsed.suspicious_lines[0]);
              }
            } else if (parsed.type === 'token') {
              accumulatedReview += parsed.token;
              setMentorReview(prev => ({
                ...(prev || {}),
                status: 'success',
                review: accumulatedReview
              }));
            }
          } catch (e) {
            // 忽略碎片 json 解析错误
          }
        }
      }

      // 将导师回复作为 assistant 角色加入上下文历史
      if (accumulatedReview.trim()) {
        setMentorChatHistory(prev => [
          ...prev,
          { role: 'assistant', content: accumulatedReview }
        ]);
      }

      if (overrideQ) setMentorQuestion('');
      // 提问完成后清空局部划词选区与浮层
      setSelectedCode('');
      setSelectionWidgetPos(null);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMentorReview({
          status: 'error',
          score: 50,
          level: 'D',
          review: `### ⚠️ AI 导师连接异常\n${err.message}\n建议检查网络连接或稍后重试。`
        });
      }
    } finally {
      setIsMentorLoading(false);
      setIsMentorStreaming(false);
    }
  };

  // 代码编辑器跳转并高亮报错调用栈行
  const jumpToLine = (lineNum) => {
    if (!lineNum || !editorInstanceRef.current) return;
    try {
      const ed = editorInstanceRef.current;
      ed.revealLineInCenter(lineNum);
      ed.setPosition({ lineNumber: lineNum, column: 1 });
      ed.focus();
      setHighlightLine(lineNum);
      showToast(`🎯 已精确聚焦至错误嫌疑代码第 ${lineNum} 行`, null, 2500);
    } catch (e) {
      console.warn('Jump to line failed:', e);
    }
  };

  // 将 Python 报错 Traceback 中的行号智能渲染为可点击交互直达组件
  const renderInteractiveStderr = (stderrText, customStyle = {}) => {
    if (!stderrText) return null;
    const lines = stderrText.split('\n');
    return (
      <div style={{ ...customStyle, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
        {lines.map((line, idx) => {
          // 匹配常见 Python 报错堆栈: File "...", line 123
          const match = line.match(/^(.*File\s+["'][^"']+["'],\s+line\s+)(\d+)(.*)$/i);
          if (match) {
            const prefix = match[1];
            const lineNum = parseInt(match[2], 10);
            const suffix = match[3];
            return (
              <div key={idx} style={{ lineHeight: 1.55 }}>
                <span>{prefix}</span>
                <span
                  onClick={() => jumpToLine(lineNum)}
                  title={`点击直达 Monaco 编辑器第 ${lineNum} 行`}
                  style={{
                    color: '#38bdf8',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    fontWeight: 700,
                    padding: '1px 4px',
                    margin: '0 2px',
                    backgroundColor: 'rgba(56, 189, 248, 0.16)',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    borderRadius: '3px',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.3)';
                    e.currentTarget.style.color = '#7dd3fc';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.16)';
                    e.currentTarget.style.color = '#38bdf8';
                  }}
                >
                  {lineNum} ➔
                </span>
                <span>{suffix}</span>
              </div>
            );
          }
          return (
            <div key={idx} style={{ lineHeight: 1.55 }}>
              {line}
            </div>
          );
        })}
      </div>
    );
  };

  // 处理多模态报错截图上传
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      showToast('⚠️ 图片大小不能超过 3MB');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setMentorImage(reader.result);
      showToast('📷 已附加报错截图，AI 导师将结合视觉多模态排查');
    };
    reader.readAsDataURL(file);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const isLight = currentTheme === 'paper';

  return (
    <main ref={containerRef} className="wb-console-pane" style={{ position: 'relative', height: '100%', overflow: 'hidden' }}>
      {/* 拖拽调节高度时的全屏防事件劫持遮罩，确保移动到Monaco或其他区域不中断拖动 */}
      {isDragging && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            cursor: 'row-resize',
            userSelect: 'none'
          }}
        />
      )}

      {/* 顶部工具栏 */}
      <div style={{
        height: '42px',
        background: 'var(--wb-bg-header)',
        borderBottom: '1px solid var(--wb-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* 动态文件切换选择器下拉菜单 */}
          <div ref={filePickerRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setShowFilePickerDropdown(prev => !prev)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: activeCodeFile ? 'rgba(99, 102, 241, 0.15)' : 'var(--wb-bg-subtle)',
                border: activeCodeFile ? '1px solid var(--wb-accent-primary)' : '1px solid var(--wb-border-subtle)',
                padding: '3px 8px',
                borderRadius: '5px',
                cursor: 'pointer',
                color: 'var(--wb-text-bright)',
                transition: 'all 0.15s ease'
              }}
              title="点击可手动选择并加载当前章节下的任意实战脚本进行独立调试"
            >
              <FileCode size={13} color={activeCodeFile ? 'var(--wb-accent-primary)' : 'var(--wb-text-sub)'} />
              <span style={{
                fontSize: '12px',
                fontFamily: 'var(--wb-font-mono)',
                color: activeCodeFile ? 'var(--wb-accent-primary)' : 'var(--wb-text-bright)',
                fontWeight: 600
              }}>
                {activeCodeFile ? activeCodeFile.name : 'solution.py'}
              </span>
              <span style={{
                fontSize: '9.5px',
                padding: '1px 5px',
                borderRadius: '3px',
                background: activeCodeFile ? 'rgba(99, 102, 241, 0.2)' : 'var(--wb-bg-hover)',
                color: activeCodeFile ? 'var(--wb-accent-primary)' : 'var(--wb-text-dim)'
              }}>
                {activeCodeFile ? '实战脚本' : '主通关解'}
              </span>
              <ChevronDown 
                size={11} 
                color="var(--wb-text-dim)" 
                style={{ 
                  transform: showFilePickerDropdown ? 'rotate(180deg)' : 'none', 
                  transition: 'transform 0.2s ease' 
                }} 
              />
            </button>

            {/* 下拉文件选择浮层 */}
            {showFilePickerDropdown && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                marginTop: '6px',
                width: '380px',
                maxHeight: '400px',
                background: 'var(--wb-bg-panel)',
                border: '1px solid var(--wb-border-active)',
                borderRadius: '8px',
                boxShadow: '0 12px 32px rgba(0, 0, 0, 0.5)',
                zIndex: 99999,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                {/* 浮层搜索栏 */}
                <div style={{
                  padding: '7px 10px',
                  background: 'var(--wb-bg-header)',
                  borderBottom: '1px solid var(--wb-border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <Search size={12} color="var(--wb-text-dim)" />
                  <input
                    type="text"
                    placeholder="筛选脚本文件 (如 01, attention, triton)..."
                    value={fileSearchQuery}
                    onChange={(e) => setFileSearchQuery(e.target.value)}
                    autoFocus
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
                  {fileSearchQuery && (
                    <button
                      onClick={() => setFileSearchQuery('')}
                      style={{ background: 'transparent', border: 'none', color: 'var(--wb-text-dim)', cursor: 'pointer', padding: 0 }}
                    >
                      <X size={11} />
                    </button>
                  )}
                </div>

                {/* 文件项滚动列表 */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }} className="wb-custom-scroll">
                  {/* 固定通关解项 */}
                  {(!fileSearchQuery || 'solution.py'.includes(fileSearchQuery.toLowerCase()) || '通关'.includes(fileSearchQuery)) && (
                    <div
                      onClick={() => {
                        onSelectCodeFile(null);
                        setShowFilePickerDropdown(false);
                      }}
                      style={{
                        padding: '6px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        background: !activeCodeFile ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                        borderLeft: !activeCodeFile ? '3px solid var(--wb-accent-primary)' : '3px solid transparent'
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontFamily: 'var(--wb-font-mono)', fontSize: '11.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                            solution.py
                          </span>
                          <span style={{ fontSize: '9.5px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(16, 185, 129, 0.12)', color: 'var(--wb-accent-success)' }}>
                            阶段主通关解
                          </span>
                        </div>
                        <div style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)', marginTop: '2px' }}>
                          核心通关目标代码 (提交评测目标)
                        </div>
                      </div>
                      {!activeCodeFile && <Check size={13} color="var(--wb-accent-primary)" />}
                    </div>
                  )}

                  {/* 遍历章节配套实战脚本 */}
                  {codeFiles && codeFiles.length > 0 && (
                    <div style={{
                      padding: '6px 12px 3px',
                      fontSize: '10px',
                      fontWeight: 600,
                      color: 'var(--wb-text-dim)',
                      textTransform: 'uppercase',
                      borderTop: '1px solid var(--wb-border-subtle)',
                      marginTop: '4px'
                    }}>
                      📁 章节配套实战源码与算子脚本 ({codeFiles.length} 个)
                    </div>
                  )}

                  {(codeFiles || [])
                    .filter(f => f.name !== 'solution.py')
                    .filter(f => {
                      if (!fileSearchQuery.trim()) return true;
                      const q = fileSearchQuery.toLowerCase();
                      return (f.name && f.name.toLowerCase().includes(q)) || (f.doc && f.doc.toLowerCase().includes(q));
                    })
                    .map((file, idx) => {
                      const isCur = activeCodeFile?.name === file.name;
                      return (
                        <div
                          key={file.name || idx}
                          onClick={() => {
                            onSelectCodeFile(file);
                            setShowFilePickerDropdown(false);
                          }}
                          style={{
                            padding: '6px 12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            background: isCur ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                            borderLeft: isCur ? '3px solid var(--wb-accent-primary)' : '3px solid transparent',
                            transition: 'background 0.15s'
                          }}
                          onMouseEnter={(e) => { if (!isCur) e.currentTarget.style.background = 'var(--wb-bg-hover)'; }}
                          onMouseLeave={(e) => { if (!isCur) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <div style={{ minWidth: 0, flex: 1, paddingRight: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontFamily: 'var(--wb-font-mono)', fontSize: '11.5px', fontWeight: isCur ? 650 : 500, color: isCur ? 'var(--wb-accent-primary)' : 'var(--wb-text-bright)' }}>
                                {file.name}
                              </span>
                              {file.name === 'starter.py' && (
                                <span style={{ fontSize: '9.5px', padding: '0 4px', borderRadius: '2px', background: 'rgba(245, 158, 11, 0.12)', color: 'var(--wb-accent-amber)' }}>
                                  起手模板
                                </span>
                              )}
                            </div>
                            {file.doc && (
                              <div style={{ fontSize: '10.5px', color: 'var(--wb-text-sub)', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                💡 {file.doc}
                              </div>
                            )}
                          </div>
                          {isCur && <Check size={13} color="var(--wb-accent-primary)" style={{ flexShrink: 0 }} />}
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
          </div>

          {/* 草稿状态指示胶囊 (Phase 2A) */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '12px',
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              color: 'var(--wb-text-dim)'
            }} 
            title="代码会防抖自动暂存在浏览器本地，刷新或切换关卡均不丢失"
          >
            {saveStatus === 'saving' ? (
              <>
                <RefreshCw size={10} className="spin-fast" style={{ color: 'var(--wb-accent-amber)' }} />
                <span style={{ color: 'var(--wb-accent-amber)' }}>自动暂存中...</span>
              </>
            ) : hasDraft ? (
              <>
                <CheckCircle2 size={10} style={{ color: 'var(--wb-accent-success)' }} />
                <span style={{ color: 'var(--wb-text-sub)' }}>
                  草稿已保存 {draftUpdatedAt ? formatDraftTime(draftUpdatedAt) : ''}
                </span>
              </>
            ) : (
              <>
                <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--wb-text-dim)' }}></span>
                <span>初始模板</span>
              </>
            )}
          </div>

          {/* 历史撤销备份快捷找回 */}
          {draftBackup && !hasDraft && (
            <button
              onClick={() => handleRestoreBackup()}
              className="wb-btn-ghost"
              style={{
                fontSize: '10.5px',
                padding: '2px 7px',
                color: 'var(--wb-accent-subtle)',
                borderColor: 'var(--wb-border-subtle)'
              }}
              title="点击找回上次被重置的代码草稿"
            >
              <Undo2 size={10} />
              <span>找回上次草稿</span>
            </button>
          )}
        </div>

        {/* 动作按钮组 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* 参考对比按钮 (Phase 2B) */}
          <button
            onClick={handleToggleDiff}
            className="wb-btn-ghost"
            style={{
              borderColor: isDiffMode ? 'var(--wb-accent-subtle)' : undefined,
              color: isDiffMode ? 'var(--wb-accent-subtle)' : undefined,
              background: isDiffMode ? 'var(--wb-bg-hover)' : undefined
            }}
            title={isDiffMode ? "退出差异对比，返回常规代码编辑" : "与官方标准参考实现进行 Diff 差异对比"}
          >
            <GitCompare size={12} />
            <span>{isDiffMode ? '退出对比' : '参考对比'}</span>
          </button>

          {/* 当处于对比模式时，显示一键采纳标准答案按钮 */}
          {isDiffMode && (
            <button
              onClick={handleAdoptSolution}
              className="wb-btn-ghost"
              style={{
                borderColor: 'var(--wb-accent-success)',
                color: 'var(--wb-accent-success)',
                background: 'var(--wb-bg-hover)'
              }}
              title="将官方标准参考答案同步覆盖至当前工作区草稿"
            >
              <Sparkles size={11} />
              <span>采纳标准答案</span>
            </button>
          )}

          {/* 重置初始模板 */}
          <button
            onClick={handleResetClick}
            className="wb-btn-ghost"
            title="重置为官方初始模板代码"
          >
            <RotateCcw size={12} />
            <span>重置</span>
          </button>

          {/* 立即保存草稿 */}
          <button
            onClick={handleSaveImmediately}
            className="wb-btn-ghost"
            title="立即将当前代码保存到本地草稿箱 (快捷键 ⌘S)"
          >
            <Save size={12} />
            <span>暂存</span>
            <kbd style={{ fontSize: '9.5px', color: 'var(--wb-text-dim)' }}>⌘S</kbd>
          </button>

          {/* 复制代码 */}
          <button
            onClick={handleCopy}
            className="wb-btn-ghost"
            title="复制代码"
          >
            <Copy size={12} />
            <span>{copied ? '已复制' : '复制'}</span>
          </button>

          {/* 代码方法自动提醒与速查助手按钮 */}
          <button
            onClick={() => setShowMethodAssistDrawer(!showMethodAssistDrawer)}
            className="wb-btn-ghost"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: showMethodAssistDrawer ? 'rgba(56, 189, 248, 0.16)' : 'var(--wb-bg-subtle)',
              borderColor: showMethodAssistDrawer ? 'rgba(56, 189, 248, 0.45)' : 'var(--wb-border-subtle)',
              color: showMethodAssistDrawer ? 'var(--wb-accent-primary, #38bdf8)' : 'var(--wb-text-bright)',
              fontSize: '11.5px',
              padding: '3px 9px',
              borderRadius: '5px',
              transition: 'all 0.2s ease'
            }}
            title={showMethodAssistDrawer ? "收起代码方法快捷助手面板" : "展开 Python / LangGraph / RAG 核心代码方法自动快捷提醒与速查抽屉"}
          >
            <Sparkles size={12} color={showMethodAssistDrawer ? '#38bdf8' : 'currentColor'} />
            <span>方法快捷提醒</span>
            <span style={{
              background: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
              fontSize: '9.5px',
              padding: '1px 5px',
              borderRadius: '8px',
              fontWeight: 600
            }}>
              自动提示
            </span>
          </button>

          {/* 运行按钮 */}
          <button
            onClick={handleRunCode}
            disabled={isRunning}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              color: 'var(--wb-text-bright)',
              fontSize: '11.5px',
              padding: '3px 10px',
              borderRadius: '5px',
              cursor: isRunning ? 'not-allowed' : 'pointer'
            }}
          >
            <Play size={11} fill="currentColor" />
            <span>运行</span>
            <kbd style={{ fontSize: '10px', color: 'var(--wb-text-dim)' }}>⌘↵</kbd>
          </button>

          {/* 验证评测 */}
          <button
            onClick={handleVerify}
            disabled={isRunning}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'var(--wb-accent-subtle)',
              border: 'none',
              color: '#ffffff',
              fontWeight: 500,
              fontSize: '11.5px',
              padding: '3px 10px',
              borderRadius: '5px',
              cursor: isRunning ? 'not-allowed' : 'pointer'
            }}
          >
            <CheckCircle size={12} />
            <span>验证通关</span>
          </button>
        </div>
      </div>

      {/* 外部配套实战脚本调试状态栏 */}
      {activeCodeFile && (
        <div style={{
          height: '32px',
          background: 'rgba(99, 102, 241, 0.08)',
          borderBottom: '1px solid rgba(99, 102, 241, 0.22)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          fontSize: '11.5px',
          color: 'var(--wb-text-bright)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0 }}>
            <Sparkles size={13} color="var(--wb-accent-primary)" style={{ flexShrink: 0 }} />
            <span style={{ color: 'var(--wb-text-sub)' }}>正在自由调试配套脚本：</span>
            <span style={{ fontFamily: 'var(--wb-font-mono)', fontWeight: 600, color: 'var(--wb-accent-primary)' }}>
              {activeCodeFile.name}
            </span>
            {activeCodeFile.doc && (
              <span style={{ color: 'var(--wb-text-dim)', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                · {activeCodeFile.doc}
              </span>
            )}
          </div>
          <button
            onClick={() => onSelectCodeFile(null)}
            className="wb-btn-ghost"
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '4px',
              color: 'var(--wb-accent-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              flexShrink: 0
            }}
            title="切回本关卡的标准通关任务代码 solution.py"
          >
            <span>切回主通关解 (solution.py)</span>
          </button>
        </div>
      )}

      {/* 浮动轻提示 Toast (支持撤销操作) */}
      {toast && (
        <div style={{
          position: 'absolute',
          top: '50px',
          right: '16px',
          zIndex: 1000,
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-border-active)',
          borderRadius: '6px',
          padding: '7px 12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '12px',
          color: 'var(--wb-text-bright)'
        }}>
          <span>{toast.message}</span>
          {toast.undoAction && (
            <button
              onClick={() => {
                toast.undoAction();
                setToast(null);
              }}
              style={{
                background: 'var(--wb-accent-subtle)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              撤销找回
            </button>
          )}
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--wb-text-dim)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '2px'
            }}
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* 外部配套脚本执行验证确认弹窗 */}
      {showVerifyExternalConfirmModal && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }} 
          onClick={() => setShowVerifyExternalConfirmModal(false)}
        >
          <div 
            style={{
              width: '100%',
              maxWidth: '460px',
              background: 'var(--wb-bg-panel)',
              border: '1px solid var(--wb-border-active)',
              borderRadius: '10px',
              padding: '20px',
              boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'rgba(99, 102, 241, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Sparkles size={18} color="var(--wb-accent-primary)" />
              </div>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 650, color: 'var(--wb-text-bright)' }}>
                  您当前正在调试配套实战脚本
                </h4>
                <p style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)' }}>
                  当前文件：<code style={{ fontFamily: 'var(--wb-font-mono)', color: 'var(--wb-accent-primary)' }}>{activeCodeFile?.name}</code>
                </p>
              </div>
            </div>

            <div style={{
              fontSize: '12.5px',
              color: 'var(--wb-text-sub)',
              lineHeight: '1.6',
              background: 'var(--wb-bg-subtle)',
              padding: '12px 14px',
              borderRadius: '6px',
              border: '1px solid var(--wb-border-subtle)'
            }}>
              💡 <strong>操作引导</strong>：本关卡的自动化单元测试针对的是核心任务通关文件 <code>solution.py</code>。<br />
              • 推荐<strong>切回 solution.py 并进行通关评测</strong>；<br />
              • 或者<strong>保持当前脚本直接评测</strong>。
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
              <button
                onClick={() => setShowVerifyExternalConfirmModal(false)}
                className="wb-btn-ghost"
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                取消
              </button>
              <button
                onClick={handleForceVerifyCurrentScript}
                className="wb-btn-ghost"
                style={{
                  fontSize: '12px',
                  padding: '6px 12px',
                  borderColor: 'var(--wb-border-subtle)',
                  color: 'var(--wb-text-bright)'
                }}
              >
                保持当前脚本评测
              </button>
              <button
                onClick={handleConfirmSwitchToSolutionAndVerify}
                style={{
                  fontSize: '12px',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  background: 'var(--wb-accent-primary)',
                  color: '#ffffff',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 650
                }}
              >
                切回 solution.py 并评测
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 重置二次确认模态弹窗 */}
      {showResetModal && (
        <div 
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }} 
          onClick={() => setShowResetModal(false)}
        >
          <div 
            style={{
              width: '100%',
              maxWidth: '420px',
              background: 'var(--wb-bg-panel)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '10px',
              padding: '20px',
              boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(234, 179, 8, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <AlertTriangle size={18} style={{ color: 'var(--wb-accent-amber)' }} />
              </div>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                  确定重置为初始关卡模板？
                </h4>
                <p style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)' }}>
                  当前关卡：{phaseId} (solution.py)
                </p>
              </div>
            </div>

            <div style={{
              fontSize: '12px',
              color: 'var(--wb-text-sub)',
              lineHeight: '1.6',
              background: 'var(--wb-bg-subtle)',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid var(--wb-border-subtle)'
            }}>
              重置将使用官方初始代码覆盖当前编辑区。为防误触，系统已为您自动保留一份撤销快照。
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
              <button
                onClick={() => setShowResetModal(false)}
                className="wb-btn-ghost"
                style={{ padding: '6px 14px', fontSize: '12px' }}
              >
                取消
              </button>
              <button
                onClick={confirmReset}
                style={{
                  background: 'var(--wb-accent-rose, #ef4444)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '6px 14px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: 'pointer'
                }}
              >
                确认重置
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 通关成功结算与下一关路线引导卡片 (Phase 2B) */}
      {showSuccessModal && successStats && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99999,
            background: 'rgba(0, 0, 0, 0.72)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
          onClick={() => setShowSuccessModal(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '460px',
              background: 'var(--wb-bg-panel)',
              border: '1px solid var(--wb-border-active)',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              animation: 'fadeIn 0.2s ease'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 顶部荣誉徽章与标题 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.25), rgba(59, 130, 246, 0.25))',
                border: '1px solid rgba(34, 197, 94, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Award size={24} style={{ color: 'var(--wb-accent-success)' }} />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                    🎉 关卡实战通关达成！
                  </h3>
                  <span style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '10px',
                    background: 'rgba(34, 197, 94, 0.15)',
                    color: 'var(--wb-accent-success)',
                    border: '1px solid rgba(34, 197, 94, 0.3)'
                  }}>
                    +{successStats.xp} XP
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--wb-text-dim)', marginTop: '2px' }}>
                  {successStats.phaseTitle || phaseId}
                </p>
              </div>
            </div>

            {/* 关键评测指标统计 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '8px',
              background: 'var(--wb-bg-subtle)',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid var(--wb-border-subtle)'
            }}>
              <div>
                <div style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>测试断言</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-accent-success)' }}>100% 通过</div>
              </div>
              <div>
                <div style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>沙箱耗时</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>{Math.round(successStats.timeMs)} ms</div>
              </div>
              <div>
                <div style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>通关权限</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-accent-subtle)' }}>解锁下一关</div>
              </div>
            </div>

            {/* 下一关路线推荐卡片 */}
            {successStats.nextPhase && (
              <div style={{
                background: 'var(--wb-bg-root)',
                border: '1px solid var(--wb-border-subtle)',
                borderRadius: '8px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>👉 推荐下一挑战</span>
                  <span style={{ fontSize: '10.5px', color: 'var(--wb-accent-subtle)' }}>
                    难度：{successStats.nextPhase.difficulty}
                  </span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--wb-text-bright)' }}>
                  {successStats.nextPhase.title}
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--wb-text-sub)', lineClamp: 2, overflow: 'hidden' }}>
                  {successStats.nextPhase.description}
                </div>
              </div>
            )}

            {/* 底部动作按钮栏 */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginTop: '6px' }}>
              <button
                onClick={() => {
                  setShowSuccessModal(false);
                  handleAskMentor('恭喜通关！请对当前满分代码进行架构级 Code Review 与企业级生产落地建议');
                }}
                className="wb-btn-ghost"
                style={{ fontSize: '11.5px', padding: '6px 12px' }}
                title="请大模型导师深度解析代码进阶优化空间"
              >
                <Sparkles size={12} />
                <span>导师进阶复盘</span>
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => setShowSuccessModal(false)}
                  className="wb-btn-ghost"
                  style={{ fontSize: '11.5px', padding: '6px 12px' }}
                >
                  留在本关
                </button>
                {successStats.nextPhase && (
                  <button
                    onClick={() => {
                      setShowSuccessModal(false);
                      onNavigatePhase(successStats.nextPhase.id);
                    }}
                    style={{
                      background: 'var(--wb-accent-success)',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '6px 16px',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                      boxShadow: '0 2px 10px rgba(34, 197, 94, 0.3)'
                    }}
                  >
                    <span>开启下一关</span>
                    <ArrowRight size={13} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Monaco 代码编辑器 / Diff 差异对比视图 (设置 minHeight: 0 允许 flex 压缩，终端向上拉伸) */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Diff 视图模式提示横幅 */}
        {isDiffMode && (
          <div style={{
            height: '28px',
            background: 'var(--wb-bg-subtle)',
            borderBottom: '1px solid var(--wb-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 12px',
            fontSize: '11px',
            color: 'var(--wb-text-sub)',
            zIndex: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--wb-accent-subtle)', fontWeight: 500 }}>
                [差异对比] 左侧：官方参考实现 (只读) ⟷ 右侧：我的当前代码 (可实时编辑)
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                onClick={handleAdoptSolution}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--wb-accent-success)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Sparkles size={11} />
                <span>一键采纳标准代码</span>
              </button>
              <button
                onClick={() => setIsDiffMode(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--wb-text-dim)',
                  cursor: 'pointer',
                  fontSize: '11px'
                }}
              >
                退出对比
              </button>
            </div>
          </div>
        )}

        {/* 未解锁前置提示条 (仅在闯关模式且当前关卡未解锁时友好展示) */}
        {isChallengeMode && !isUnlocked && (
          <div style={{
            background: 'rgba(234, 179, 8, 0.08)',
            borderBottom: '1px solid rgba(234, 179, 8, 0.22)',
            padding: '6px 12px',
            fontSize: '11.5px',
            color: 'var(--wb-accent-amber)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            zIndex: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={12} />
              <span>本关卡前置依赖尚未全部达成（建议依序完成前置关卡以建立认知底座）</span>
            </div>
            <button
              onClick={onToggleChallengeMode}
              style={{
                background: 'none',
                border: '1px solid rgba(234, 179, 8, 0.35)',
                borderRadius: '4px',
                color: 'var(--wb-accent-amber)',
                fontSize: '10.5px',
                padding: '2px 8px',
                cursor: 'pointer'
              }}
              title="切换为自由模式免锁演练"
            >
              一键切换自由模式
            </button>
          </div>
        )}

        {/* 代码编辑区与 Diff 审查区 */}
        <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column' }}>
          {/* 常用代码方法自动快捷提醒与速查助手面板 */}
          {showMethodAssistDrawer && (
            <div style={{
              background: 'var(--wb-bg-subtle, #0f131d)',
              borderBottom: '1px solid rgba(56, 189, 248, 0.25)',
              padding: '10px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              zIndex: 20,
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)'
            }}>
              {/* 顶部搜索与分类过滤 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '220px' }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.12))',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    width: '100%',
                    maxWidth: '280px'
                  }}>
                    <Search size={12} color="var(--wb-text-dim)" />
                    <input
                      type="text"
                      value={searchMethodQuery}
                      onChange={(e) => setSearchMethodQuery(e.target.value)}
                      placeholder="搜索代码方法、类名或关键字..."
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--wb-text-bright, #fff)',
                        fontSize: '11px',
                        outline: 'none',
                        width: '100%'
                      }}
                    />
                    {searchMethodQuery && (
                      <button
                        onClick={() => setSearchMethodQuery('')}
                        style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', padding: 0 }}
                      >
                        <X size={11} />
                      </button>
                    )}
                  </div>

                  {/* 分类过滤胶囊 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', overflowX: 'auto' }}>
                    {['ALL', 'LangGraph 智能体状态图', '大模型调用 (OpenAI / DeepSeek)', '向量检索与 Hybrid RAG', '企业安全与运维治理', 'Python 异步与工程常用'].map((cat) => {
                      const isSelected = selectedMethodCategory === cat;
                      const label = cat === 'ALL' ? '全部方法' : cat.split(' ')[0];
                      return (
                        <button
                          key={cat}
                          onClick={() => setSelectedMethodCategory(cat)}
                          style={{
                            background: isSelected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                            border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.45)' : 'rgba(255, 255, 255, 0.08)'}`,
                            color: isSelected ? '#38bdf8' : 'var(--wb-text-dim, #94a3b8)',
                            fontSize: '10.5px',
                            padding: '2px 7px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '10.5px', color: 'var(--wb-text-dim, #888)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Lightbulb size={11} color="#fbbf24" />
                    <span>按 <kbd style={{ fontSize: '9px', background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: '3px' }}>Ctrl+Space</kbd> 呼出自动补全</span>
                  </span>
                  <button
                    onClick={() => setShowMethodAssistDrawer(false)}
                    className="wb-btn-ghost"
                    style={{ fontSize: '10.5px', padding: '2px 6px' }}
                    title="收起方法速查面板"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>

              {/* 方法卡片列表 */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: '8px',
                maxHeight: '180px',
                overflowY: 'auto',
                paddingRight: '4px'
              }}>
                {PYTHON_METHODS_CATALOG
                  .filter((item) => {
                    if (selectedMethodCategory !== 'ALL' && item.category !== selectedMethodCategory) return false;
                    if (!searchMethodQuery) return true;
                    const q = searchMethodQuery.toLowerCase();
                    return item.name.toLowerCase().includes(q) || 
                           item.signature.toLowerCase().includes(q) || 
                           item.doc.toLowerCase().includes(q);
                  })
                  .map((item) => {
                    const isJustInserted = insertedMethodName === item.name;
                    return (
                      <div
                        key={item.name}
                        style={{
                          background: 'rgba(255, 255, 255, 0.025)',
                          border: '1px solid rgba(255, 255, 255, 0.07)',
                          borderRadius: '6px',
                          padding: '7px 10px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '4px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                              fontFamily: 'var(--wb-font-mono)',
                              fontSize: '12px',
                              fontWeight: 700,
                              color: 'var(--wb-accent-primary, #38bdf8)'
                            }}>
                              {item.name}
                            </span>
                            <span style={{
                              fontSize: '9.5px',
                              padding: '1px 5px',
                              borderRadius: '3px',
                              background: item.kind === 'Class' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(52, 211, 153, 0.15)',
                              color: item.kind === 'Class' ? '#c084fc' : '#34d399',
                              border: `1px solid ${item.kind === 'Class' ? 'rgba(168, 85, 247, 0.3)' : 'rgba(52, 211, 153, 0.3)'}`
                            }}>
                              {item.kind}
                            </span>
                          </div>

                          <button
                            onClick={() => handleInsertMethod(item)}
                            style={{
                              background: isJustInserted ? 'rgba(34, 197, 94, 0.2)' : 'rgba(56, 189, 248, 0.1)',
                              border: `1px solid ${isJustInserted ? 'rgba(34, 197, 94, 0.5)' : 'rgba(56, 189, 248, 0.3)'}`,
                              color: isJustInserted ? '#4ade80' : '#38bdf8',
                              fontSize: '10.5px',
                              padding: '2px 7px',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              transition: 'all 0.18s ease'
                            }}
                            title="将该方法模版直接插入到代码编辑器当前光标处"
                          >
                            {isJustInserted ? <Check size={11} /> : <Code2 size={11} />}
                            <span>{isJustInserted ? '已插入' : '一键插入'}</span>
                          </button>
                        </div>

                        <div style={{
                          fontSize: '10.5px',
                          color: 'var(--wb-text-sub, #94a3b8)',
                          lineHeight: '1.4',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical'
                        }}>
                          {item.doc}
                        </div>

                        <div style={{
                          fontSize: '10px',
                          fontFamily: 'var(--wb-font-mono)',
                          color: 'var(--wb-text-dim, #64748b)',
                          background: 'rgba(0,0,0,0.25)',
                          padding: '2px 5px',
                          borderRadius: '3px',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {item.signature}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Diff 模式下的工程审查出处标头栏 (解决出处缺失与为了对比而对比) */}
          {isDiffMode && (() => {
            const diffMeta = getDiffMeta();
            return (
              <div style={{
                background: 'var(--wb-bg-subtle, #12151e)',
                borderBottom: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                padding: '8px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                zIndex: 10
              }}>
                {/* 顶排：双栏出处对齐与来源切换 */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  {/* 左栏基准来源选择与出处标定 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', fontWeight: 600 }}>
                      基准参考来源 (左):
                    </span>
                    <select
                      value={diffBaseSource}
                      onChange={(e) => setDiffBaseSource(e.target.value)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.15))',
                        borderRadius: '5px',
                        color: '#fff',
                        fontSize: '11px',
                        padding: '3px 8px',
                        outline: 'none',
                        cursor: 'pointer'
                      }}
                      title="选择要与当前代码进行 Diff 对比的基准版本"
                    >
                      <option value="solution" style={{ background: '#181b24', color: '#fff' }}>
                        🌟 官方标准架构实现 ({solutionSource ? solutionSource.split(' ')[0] : 'solution.py'})
                      </option>
                      <option value="passed" style={{ background: '#181b24', color: '#fff' }}>
                        🕒 我的历史通关快照 {getPassedCode() ? '(已归档)' : '(暂无通关记录)'}
                      </option>
                      <option value="starter" style={{ background: '#181b24', color: '#fff' }}>
                        📦 官方初始起步脚手架 (starter.py)
                      </option>
                    </select>

                    {/* 出处文件路径与版本徽章 */}
                    <span style={{
                      fontSize: '10px',
                      fontFamily: 'monospace',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: diffMeta.tagBg,
                      border: `1px solid ${diffMeta.tagColor}40`,
                      color: diffMeta.tagColor,
                      fontWeight: 600
                    }}>
                      出处: {diffMeta.sourcePath}
                    </span>
                  </div>

                  {/* 右栏：当前工作区与采纳操作 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--wb-text-sub, #aaa)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span>当前工作草稿 (右):</span>
                      <strong style={{ color: '#fff' }}>本地实时编辑区</strong>
                    </div>
                    <button
                      onClick={handleAdoptSolution}
                      className="wb-btn-ghost"
                      style={{
                        fontSize: '11px',
                        padding: '3px 8px',
                        color: 'var(--wb-accent-success, #4ade80)',
                        borderColor: 'rgba(74, 222, 128, 0.3)',
                        background: 'rgba(74, 222, 128, 0.08)'
                      }}
                      title="将左侧选中的基准代码同步覆盖至当前工作草稿"
                    >
                      <Sparkles size={11} />
                      <span>采纳当前基准</span>
                    </button>
                    <button
                      onClick={() => setIsDiffMode(false)}
                      className="wb-btn-ghost"
                      style={{ fontSize: '11px', padding: '3px 8px' }}
                      title="退出对比，返回常规单栏代码编辑器"
                    >
                      退出对比
                    </button>
                  </div>
                </div>

                {/* 底排：审查目的与架构设计意图导引 */}
                <div style={{
                  fontSize: '11px',
                  color: 'var(--wb-text-dim, #94a3b8)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  lineHeight: 1.4,
                  paddingTop: '2px'
                }}>
                  <Lightbulb size={12} color="#fbbf24" style={{ flexShrink: 0 }} />
                  <span>
                    <strong style={{ color: 'var(--wb-text-sub, #cbd5e1)' }}>审查目的与架构导引</strong>：{diffMeta.architectureDoc}
                    {diffMeta.emptyNotice && (
                      <strong style={{ color: '#fbbf24', marginLeft: '6px' }}>({diffMeta.emptyNotice})</strong>
                    )}
                  </span>
                </div>
              </div>
            );
          })()}

          {/* Monaco 编辑器核心区 */}
          <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
            {isDiffMode ? (
              <DiffEditor
                height="100%"
                language="python"
                theme={isLight ? 'vs' : 'vs-dark'}
                original={getDiffMeta().code}
                modified={code}
                onMount={(editor) => {
                  const modifiedEditor = editor.getModifiedEditor();
                  modifiedEditor.onDidChangeModelContent(() => {
                    handleCodeChange(modifiedEditor.getValue());
                  });
                }}
                options={{
                  readOnly: false,
                  originalEditable: false,
                  fontSize: 13,
                  fontFamily: 'var(--wb-font-mono)',
                  renderSideBySide: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  padding: { top: 10, bottom: 10 }
                }}
              />
            ) : (
              <Editor
                height="100%"
                defaultLanguage="python"
                theme={isLight ? 'vs' : 'vs-dark'}
                value={code}
                onChange={handleCodeChange}
                onMount={handleEditorMount}
                options={{
                  fontSize: 13,
                  fontFamily: 'var(--wb-font-mono)',
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                  lineNumbers: 'on',
                  renderLineHighlight: 'line',
                  padding: { top: 12, bottom: 12 },
                  quickSuggestions: { other: true, comments: false, strings: true },
                  suggestOnTriggerCharacters: true,
                  acceptSuggestionOnEnter: 'on',
                  tabCompletion: 'on',
                  parameterHints: { enabled: true },
                  suggest: {
                    showMethods: true,
                    showFunctions: true,
                    showClasses: true,
                    showSnippets: true,
                    showVariables: true,
                    showWords: true
                  }
                }}
              />
            )}

            {/* 编辑器划词定向提问悬浮气泡 Widget */}
            {selectionWidgetPos && selectedCode && !isDiffMode && (
              <div
                style={{
                  position: 'absolute',
                  top: `${selectionWidgetPos.top}px`,
                  left: `${selectionWidgetPos.left}px`,
                  zIndex: 100,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'var(--wb-bg-panel, #1e2230)',
                  border: '1px solid rgba(59, 130, 246, 0.4)',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                  borderRadius: '6px',
                  padding: '3px 6px',
                  animation: 'fadeIn 0.15s ease'
                }}
              >
                <button
                  onClick={() => {
                    handleAskMentor(`请重点针对我选中的这段代码片段进行深入剖析：它是如何运转的？是否存在隐藏边界缺陷或性能隐患？`);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: 'rgba(59, 130, 246, 0.2)',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    color: '#60a5fa',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                  title="向 AI 导师提问选中的这几行代码"
                >
                  <Sparkles size={11} color="#60a5fa" />
                  <span>💡 提问选中代码</span>
                </button>
                <button
                  onClick={() => {
                    setSelectionWidgetPos(null);
                    setSelectedCode('');
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--wb-text-dim)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '2px'
                  }}
                >
                  <X size={11} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 底部可拉伸伸缩抽屉控制台 (flexShrink: 0 严禁被 flex 压缩) */}
      <div 
        className="wb-terminal" 
        style={{ 
          height: isTerminalCollapsed 
            ? '34px' 
            : isTerminalMaximized 
              ? 'calc(100% - 42px)' 
              : `${terminalHeight}px`,
          minHeight: isTerminalCollapsed ? '34px' : '100px',
          flexShrink: 0,
          transition: isDragging ? 'none' : 'height 0.2s cubic-bezier(0.16, 1, 0.3, 1), background 0.2s ease',
          userSelect: isDragging ? 'none' : 'auto',
          position: 'relative'
        }}
      >
        {/* 顶部拖拽把手 (增大热区至 14px，跨越分界线，上下双向拉动丝滑灵敏) */}
        <div
          onMouseDown={handleMouseDownResize}
          onDoubleClick={toggleCollapse}
          title="按住鼠标上下拖拽调整高度，双击折叠/展开"
          style={{
            height: '14px',
            width: '100%',
            cursor: 'row-resize',
            position: 'absolute',
            top: '-7px',
            left: 0,
            right: 0,
            zIndex: 40,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none'
          }}
        >
          <div style={{
            width: '46px',
            height: '3px',
            borderRadius: '2px',
            background: isDragging ? 'var(--wb-accent-primary)' : 'var(--wb-border-subtle)',
            opacity: isDragging ? 1 : 0.6,
            transition: isDragging ? 'none' : 'background 0.2s, opacity 0.2s'
          }} />
        </div>

        {/* Tab 控制头 */}
        <div 
          onDoubleClick={(e) => {
            if (e.target === e.currentTarget) toggleCollapse();
          }}
          style={{
            height: '34px',
            minHeight: '34px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: isTerminalCollapsed ? 'none' : '1px solid var(--wb-border-subtle)',
            background: 'var(--wb-bg-header)',
            padding: '0 8px',
            userSelect: 'none'
          }}
        >
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => {
                setActiveTab('terminal');
                setIsTerminalCollapsed(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: activeTab === 'terminal' && !isTerminalCollapsed ? 'var(--wb-bg-subtle)' : 'transparent',
                border: activeTab === 'terminal' && !isTerminalCollapsed ? '1px solid var(--wb-border-subtle)' : '1px solid transparent',
                color: activeTab === 'terminal' && !isTerminalCollapsed ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11.5px',
                cursor: 'pointer'
              }}
            >
              <Terminal size={12} />
              <span>控制台输出</span>
            </button>

            <button
              onClick={() => {
                setActiveTab('test');
                setIsTerminalCollapsed(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: activeTab === 'test' && !isTerminalCollapsed ? 'var(--wb-bg-subtle)' : 'transparent',
                border: activeTab === 'test' && !isTerminalCollapsed ? '1px solid var(--wb-border-subtle)' : '1px solid transparent',
                color: activeTab === 'test' && !isTerminalCollapsed ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11.5px',
                cursor: 'pointer'
              }}
            >
              <CheckCircle2 size={12} />
              <span>评测详情</span>
              {verifyResult && (
                <span style={{
                  fontSize: '9.5px',
                  padding: '0 4px',
                  borderRadius: '3px',
                  background: verifyResult.passed ? 'rgba(34, 197, 94, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                  color: verifyResult.passed ? '#4ade80' : '#fb7185'
                }}>
                  {verifyResult.passed ? 'PASS' : 'FAIL'}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                setActiveTab('mentor');
                setIsTerminalCollapsed(false);
                if (!mentorReview) handleAskMentor();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: activeTab === 'mentor' && !isTerminalCollapsed ? 'var(--wb-bg-subtle)' : 'transparent',
                border: activeTab === 'mentor' && !isTerminalCollapsed ? '1px solid var(--wb-border-subtle)' : '1px solid transparent',
                color: activeTab === 'mentor' && !isTerminalCollapsed ? 'var(--wb-accent-primary)' : 'var(--wb-text-sub)',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11.5px',
                cursor: 'pointer'
              }}
            >
              <Sparkles size={12} color="var(--wb-accent-primary)" />
              <span>AI 伴学诊断</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* 控制台专属工具栏 (仅在控制台输出 Tab 展开时显示) */}
            {activeTab === 'terminal' && !isTerminalCollapsed && runResult && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {/* 搜索过滤输入框 */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'var(--wb-bg-subtle, rgba(255,255,255,0.04))',
                  border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.1))',
                  borderRadius: '4px',
                  padding: '1px 6px',
                  gap: '4px'
                }}>
                  <Search size={10} color="var(--wb-text-dim)" />
                  <input
                    type="text"
                    value={consoleSearchQuery}
                    onChange={(e) => setConsoleSearchQuery(e.target.value)}
                    placeholder="过滤日志..."
                    style={{
                      background: 'transparent',
                      border: 'none',
                      outline: 'none',
                      fontSize: '10.5px',
                      color: 'var(--wb-text-bright)',
                      width: '75px'
                    }}
                  />
                  {consoleSearchQuery && (
                    <button
                      onClick={() => setConsoleSearchQuery('')}
                      style={{ background: 'transparent', border: 'none', color: 'var(--wb-text-dim)', cursor: 'pointer', padding: 0 }}
                    >
                      <X size={10} />
                    </button>
                  )}
                </div>

                {/* 分级过滤分段器 */}
                <div style={{
                  display: 'flex',
                  background: 'var(--wb-bg-subtle, rgba(255,255,255,0.04))',
                  padding: '1px',
                  borderRadius: '4px',
                  border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))'
                }}>
                  <button
                    onClick={() => setConsoleFilter('all')}
                    style={{
                      padding: '1px 6px',
                      fontSize: '10px',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      background: consoleFilter === 'all' ? 'var(--wb-bg-hover, rgba(255,255,255,0.12))' : 'transparent',
                      color: consoleFilter === 'all' ? '#fff' : 'var(--wb-text-dim)'
                    }}
                    title="显示全部标准输出与错误日志"
                  >
                    全部
                  </button>
                  <button
                    onClick={() => setConsoleFilter('stdout')}
                    style={{
                      padding: '1px 6px',
                      fontSize: '10px',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      background: consoleFilter === 'stdout' ? 'var(--wb-bg-hover, rgba(255,255,255,0.12))' : 'transparent',
                      color: consoleFilter === 'stdout' ? '#60a5fa' : 'var(--wb-text-dim)'
                    }}
                    title="仅显示 stdout 打印日志"
                  >
                    stdout
                  </button>
                  <button
                    onClick={() => setConsoleFilter('stderr')}
                    style={{
                      padding: '1px 6px',
                      fontSize: '10px',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      background: consoleFilter === 'stderr' ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                      color: consoleFilter === 'stderr' ? '#f87171' : 'var(--wb-text-dim)'
                    }}
                    title="仅显示 stderr 错误堆栈"
                  >
                    stderr
                  </button>
                </div>

                {/* 清屏按钮 */}
                <button
                  onClick={() => {
                    setRunResult(null);
                    setConsoleSearchQuery('');
                  }}
                  className="wb-btn-ghost"
                  style={{ padding: '2px 5px', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px' }}
                  title="清空当前控制台输出"
                >
                  <Trash2 size={10} />
                  <span>清屏</span>
                </button>
              </div>
            )}

            {runResult && !isTerminalCollapsed && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>
                <span style={{
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.05)',
                  fontFamily: 'monospace'
                }}>
                  {runResult.execution_time_ms}ms
                </span>
                <span style={{
                  padding: '1px 5px',
                  borderRadius: '3px',
                  fontWeight: 600,
                  background: runResult.status === 'success' && runResult.exit_code === 0 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: runResult.status === 'success' && runResult.exit_code === 0 ? '#4ade80' : '#f87171'
                }}>
                  Exit {runResult.exit_code ?? 0}
                </span>
              </div>
            )}

            {/* 最大化 / 还原按钮 */}
            {!isTerminalCollapsed && (
              <button
                onClick={toggleMaximize}
                className="wb-btn-ghost"
                style={{ padding: '2px 4px' }}
                title={isTerminalMaximized ? '还原高度' : '最大化控制台'}
              >
                {isTerminalMaximized ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
              </button>
            )}

            {/* 折叠 / 展开控制按钮 */}
            <button
              onClick={toggleCollapse}
              className="wb-btn-ghost"
              style={{ padding: '2px 4px' }}
              title={isTerminalCollapsed ? '展开控制台 (恢复记忆高度)' : '最小化控制台'}
            >
              {isTerminalCollapsed ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>
        </div>

        {/* 抽屉内容区 */}
        {!isTerminalCollapsed && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 14px' }} className="wb-custom-scroll">
            {activeTab === 'terminal' && (
              <div>
                {!runResult ? (
                  <div style={{ color: 'var(--wb-text-dim)', fontSize: '12px' }}>
                    等待运行。点击【运行】或按下 ⌘+Enter 即可在隔离沙箱中执行。
                  </div>
                ) : (
                  <div>
                    {(() => {
                      // 根据搜索词和分级过滤动态筛选日志行
                      const filterText = (text) => {
                        if (!text) return '';
                        if (!consoleSearchQuery.trim()) return text;
                        const q = consoleSearchQuery.toLowerCase();
                        return text
                          .split('\n')
                          .filter(line => line.toLowerCase().includes(q))
                          .join('\n');
                      };

                      const showStdout = (consoleFilter === 'all' || consoleFilter === 'stdout');
                      const showStderr = (consoleFilter === 'all' || consoleFilter === 'stderr');

                      const filteredStdout = showStdout ? filterText(runResult.stdout) : '';
                      const filteredStderr = showStderr ? filterText(runResult.stderr) : '';

                      const hasAnyOutput = Boolean(filteredStdout || filteredStderr);

                      if (consoleSearchQuery && !hasAnyOutput) {
                        return (
                          <div style={{ color: 'var(--wb-text-dim)', fontSize: '12px', padding: '16px 0', textAlign: 'center' }}>
                            🔍 未找到匹配关键字「{consoleSearchQuery}」的日志行
                          </div>
                        );
                      }

                      return (
                        <>
                          {filteredStdout && (
                            <pre style={{ margin: 0, color: 'var(--wb-text-bright)', whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                              {filteredStdout}
                            </pre>
                          )}
                          {filteredStderr && (
                            <div style={{ margin: filteredStdout ? '6px 0 0' : 0, color: '#fb7185', fontSize: '12px' }}>
                              {renderInteractiveStderr(filteredStderr)}
                            </div>
                          )}
                        </>
                      );
                    })()}

                    {/* 多租户算力扣减与调度流水反馈 */}
                    {runResult.tenant_quota && (
                      <div style={{
                        marginTop: '12px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '11px',
                        color: 'var(--wb-text-sub, #aaa)'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Building2 size={12} color="var(--wb-accent-primary, #3b82f6)" />
                          <span>承担租户: <strong style={{ color: '#fff' }}>{runResult.tenant_name || currentTenant?.tenant_name}</strong></span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                            <Zap size={11} color="#fbbf24" />
                            <span>扣减: <strong style={{ color: '#fbbf24' }}>120 Tokens</strong></span>
                          </span>
                          <span>|</span>
                          <span>剩余可用: <strong style={{ color: runResult.tenant_quota.tokens_remaining <= 200 ? '#f87171' : '#4ade80' }}>{runResult.tenant_quota.tokens_remaining?.toLocaleString()} Tokens</strong></span>
                        </div>
                      </div>
                    )}

                    {/* 运行异常时提供一键诊断引导 */}
                    {(runResult.exit_code !== 0 || runResult.stderr) && (
                      <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          onClick={() => handleAskMentor('当前代码运行产生了异常报错，请为我进行苏格拉底式启发排障，指出逻辑偏差但不要直接给出答案代码。')}
                          style={{
                            background: 'rgba(59, 130, 246, 0.12)',
                            color: 'var(--wb-accent-primary)',
                            border: '1px solid rgba(59, 130, 246, 0.3)',
                            borderRadius: '6px',
                            padding: '5px 12px',
                            fontSize: '11.5px',
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                          title="呼叫 AI 导师分析此报错堆栈"
                        >
                          <Sparkles size={12} />
                          <span>💡 呼叫 AI 导师启发式排障</span>
                        </button>
                        <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>
                          提示：AI 导师将为您剖析报错诱因并提供思考线索
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'test' && (
              <div>
                {!verifyResult ? (
                  <div style={{ color: 'var(--wb-text-dim)', fontSize: '12px' }}>
                    点击【验证通关】开始跑当前阶段自动化单元测试。
                  </div>
                ) : (
                  <div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      marginBottom: '8px',
                      fontSize: '12px',
                      color: verifyResult.passed ? '#4ade80' : '#fb7185'
                    }}>
                      {verifyResult.passed ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
                      <span style={{ fontWeight: 500 }}>{verifyResult.message}</span>
                    </div>

                    {verifyResult.details?.stdout && (
                      <pre style={{ color: 'var(--wb-text-normal)', fontSize: '11.5px', whiteSpace: 'pre-wrap', margin: 0 }}>
                        {verifyResult.details.stdout}
                      </pre>
                    )}
                    {verifyResult.details?.stderr && (
                      <div style={{ color: '#fb7185', fontSize: '11.5px', marginTop: '4px' }}>
                        {renderInteractiveStderr(verifyResult.details.stderr)}
                      </div>
                    )}

                    {/* 💡 测试未通过时的 AI 导师启发式排障支架卡片 */}
                    {!verifyResult.passed && (
                      <div style={{
                        marginTop: '14px',
                        padding: '12px 14px',
                        background: 'rgba(239, 68, 68, 0.05)',
                        border: '1px solid rgba(239, 68, 68, 0.22)',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '12px',
                        animation: 'fadeIn 0.2s ease'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            background: 'rgba(59, 130, 246, 0.15)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0
                          }}>
                            <Sparkles size={16} color="var(--wb-accent-primary)" />
                          </div>
                          <div>
                            <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                              测试未通过？呼叫 AI 导师启发式排障
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--wb-text-dim)', marginTop: '2px' }}>
                              深入分析断言与逻辑偏差，提供思考支架与排查线索（严禁直接泄题，助您自主攻克）
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleAskMentor('当前关卡自动化单元测试未通过，请为我进行苏格拉底式启发排障，指出逻辑偏差但不要直接给出答案代码。')}
                          style={{
                            background: 'var(--wb-accent-subtle)',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '6px 14px',
                            fontSize: '11.5px',
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            flexShrink: 0,
                            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
                          }}
                        >
                          <Sparkles size={13} />
                          <span>一键启发式排障</span>
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'mentor' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {isMentorLoading ? (
                  <div style={{
                    padding: '28px 16px',
                    textAlign: 'center',
                    background: 'var(--wb-bg-subtle)',
                    borderRadius: '8px',
                    border: '1px solid var(--wb-border-subtle)'
                  }}>
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      color: 'var(--wb-accent-primary)',
                      fontSize: '13px',
                      fontWeight: 600,
                      marginBottom: '8px'
                    }}>
                      <Sparkles size={16} className="animate-spin" />
                      <span>AI 架构导师正在进行启发式排障与伴学诊断...</span>
                    </div>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'center',
                      gap: '20px',
                      fontSize: '11.5px',
                      color: 'var(--wb-text-dim)',
                      flexWrap: 'wrap'
                    }}>
                      <span>① 提取错误根因</span>
                      <span>② DFL 决策意图分析</span>
                      <span>③ 扫描嫌疑逻辑行</span>
                      <span>④ 生成启发式思考支架</span>
                    </div>
                  </div>
                ) : mentorReview ? (
                  <div style={{
                    background: 'var(--wb-bg-subtle)',
                    border: '1px solid var(--wb-border-subtle)',
                    borderRadius: '8px',
                    padding: '14px 16px'
                  }}>
                    {/* 顶部诊断看板 (区分排障模式与评审模式) */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      paddingBottom: '12px',
                      marginBottom: '12px',
                      borderBottom: '1px solid var(--wb-border-subtle)',
                      flexWrap: 'wrap',
                      gap: '8px'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {mentorReview.mode === 'troubleshooting' ? (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '3px 10px',
                            borderRadius: '6px',
                            background: 'rgba(234, 179, 8, 0.15)',
                            border: '1px solid rgba(234, 179, 8, 0.3)'
                          }}>
                            <Sparkles size={14} color="#fbbf24" />
                            <span style={{
                              fontSize: '12px',
                              fontWeight: 600,
                              color: '#fbbf24'
                            }}>
                              启发式排障诊断 · 苏格拉底模式
                            </span>
                          </div>
                        ) : (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '3px 10px',
                            borderRadius: '6px',
                            background: (mentorReview.score || 85) >= 80 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                            border: `1px solid ${(mentorReview.score || 85) >= 80 ? 'rgba(34, 197, 94, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`
                          }}>
                            <Award size={14} color={(mentorReview.score || 85) >= 80 ? '#4ade80' : '#60a5fa'} />
                            <span style={{
                              fontSize: '12px',
                              fontWeight: 600,
                              color: (mentorReview.score || 85) >= 80 ? '#4ade80' : '#60a5fa'
                            }}>
                              代码健康度: {mentorReview.score || 85} 分 · 等级 {mentorReview.level || 'A'}
                            </span>
                          </div>
                        )}

                        {mentorReview.dfl_decision && (
                          <span style={{
                            fontSize: '11px',
                            color: 'var(--wb-text-dim)',
                            background: 'var(--wb-bg-hover)',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            border: '1px solid var(--wb-border-subtle)'
                          }}>
                            DFL 置信度: {Math.round((mentorReview.dfl_decision.confidence || 0.85) * 100)}%
                          </span>
                        )}

                        {/* 错误调用栈精确定位标签 (点击直达对应行) */}
                        {suspiciousLines.length > 0 && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                            <span style={{ fontSize: '11px', color: '#fb7185', fontWeight: 600 }}>堆栈定位:</span>
                            {suspiciousLines.map(ln => (
                              <button
                                key={ln}
                                onClick={() => jumpToLine(ln)}
                                style={{
                                  background: highlightLine === ln ? 'rgba(239, 68, 68, 0.3)' : 'rgba(239, 68, 68, 0.12)',
                                  border: '1px solid rgba(239, 68, 68, 0.35)',
                                  color: '#f87171',
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '3px'
                                }}
                                title={`点击直接在编辑器中聚焦第 ${ln} 行错误嫌疑代码`}
                              >
                                <AlertCircle size={11} />
                                <span>第 {ln} 行</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {isMentorStreaming && (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontSize: '11px',
                            color: 'var(--wb-accent-primary)'
                          }}>
                            <Sparkles size={12} className="animate-spin" />
                            <span>实时流式推理中...</span>
                          </div>
                        )}
                        <button
                          onClick={() => handleAskMentor()}
                          disabled={isMentorStreaming}
                          className="wb-btn-ghost"
                          style={{ fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '4px', padding: '3px 8px' }}
                          title="重新发起全方位深度诊断"
                        >
                          <RefreshCw size={11} className={isMentorStreaming ? 'animate-spin' : ''} />
                          <span>重新诊断</span>
                        </button>
                      </div>
                    </div>

                    {/* Markdown 富文本诊断报告主体 (支持流式打字机闪烁光标) */}
                    <div style={{ fontSize: '12.5px', lineHeight: '1.7', color: 'var(--wb-text-normal)' }}>
                      <ReactMarkdown
                        components={{
                          h1: ({node, ...props}) => <h1 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright)', borderBottom: '1px solid var(--wb-border-subtle)', paddingBottom: '5px', margin: '14px 0 8px' }} {...props} />,
                          h2: ({node, ...props}) => <h2 style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--wb-text-bright)', margin: '12px 0 6px' }} {...props} />,
                          h3: ({node, ...props}) => <h3 style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-accent-primary)', margin: '10px 0 4px' }} {...props} />,
                          p: ({node, ...props}) => <p style={{ marginBottom: '8px' }} {...props} />,
                          blockquote: ({node, ...props}) => (
                            <blockquote style={{
                              borderLeft: '3px solid var(--wb-accent-primary)',
                              padding: '6px 12px',
                              margin: '8px 0',
                              color: 'var(--wb-text-sub)',
                              background: 'var(--wb-bg-hover)',
                              borderRadius: '0 6px 6px 0'
                            }} {...props} />
                          ),
                          table: ({node, ...props}) => (
                            <div style={{ overflowX: 'auto', margin: '8px 0' }}>
                              <table style={{
                                width: '100%',
                                borderCollapse: 'collapse',
                                fontSize: '11.5px',
                                background: 'var(--wb-bg-root)',
                                border: '1px solid var(--wb-border-subtle)'
                              }} {...props} />
                            </div>
                          ),
                          th: ({node, ...props}) => (
                            <th style={{
                              background: 'var(--wb-bg-header)',
                              border: '1px solid var(--wb-border-subtle)',
                              padding: '5px 8px',
                              textAlign: 'left',
                              fontWeight: 600,
                              color: 'var(--wb-text-bright)'
                            }} {...props} />
                          ),
                          td: ({node, ...props}) => (
                            <td style={{
                              border: '1px solid var(--wb-border-subtle)',
                              padding: '5px 8px',
                              color: 'var(--wb-text-normal)'
                            }} {...props} />
                          ),
                          pre: ({node, children, ...props}) => {
                            // 提取子元素中的纯文本代码内容
                            let rawCode = '';
                            try {
                              const codeElement = React.Children.toArray(children)[0];
                              if (codeElement && codeElement.props && codeElement.props.children) {
                                rawCode = String(codeElement.props.children);
                              } else {
                                rawCode = String(children);
                              }
                            } catch {
                              rawCode = String(children);
                            }
                            const isCodeBlock = rawCode && rawCode.trim().length > 0;

                            return (
                              <div style={{ position: 'relative', margin: '8px 0' }}>
                                {isCodeBlock && (
                                  <div style={{
                                    position: 'absolute',
                                    top: '6px',
                                    right: '8px',
                                    display: 'flex',
                                    gap: '6px',
                                    zIndex: 10
                                  }}>
                                    <button
                                      type="button"
                                      onClick={() => handleApplyMentorSnippet(rawCode)}
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px',
                                        background: 'rgba(59, 130, 246, 0.25)',
                                        border: '1px solid rgba(59, 130, 246, 0.4)',
                                        color: '#60a5fa',
                                        fontSize: '10.5px',
                                        padding: '2px 8px',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        transition: 'all 0.15s'
                                      }}
                                      title="一键将 AI 导师推荐的代码回填应用到编辑区 (自动备份当前草稿)"
                                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.4)'}
                                      onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.25)'}
                                    >
                                      <span>🚀 应用到编辑区</span>
                                    </button>
                                  </div>
                                )}
                                <pre style={{
                                  background: 'var(--wb-bg-root)',
                                  border: '1px solid var(--wb-border-subtle)',
                                  borderRadius: '6px',
                                  padding: '10px 12px',
                                  overflowX: 'auto',
                                  fontFamily: 'var(--wb-font-mono)',
                                  fontSize: '11.5px',
                                  margin: 0
                                }} {...props}>
                                  {children}
                                </pre>
                              </div>
                            );
                          },
                          code: ({node, className, children, ...props}) => {
                            const isBlock = String(children).includes('\n') || (className && className.includes('language-'));
                            return isBlock ? (
                              <code style={{ fontFamily: 'var(--wb-font-mono)', color: 'var(--wb-text-bright)' }} {...props}>
                                {children}
                              </code>
                            ) : (
                              <code style={{
                                background: 'var(--wb-bg-hover)',
                                color: 'var(--wb-accent-primary)',
                                padding: '1px 4px',
                                borderRadius: '3px',
                                fontFamily: 'var(--wb-font-mono)',
                                fontSize: '11px'
                              }} {...props}>
                                {children}
                              </code>
                            );
                          },
                          ul: ({node, ...props}) => <ul style={{ paddingLeft: '18px', marginBottom: '6px' }} {...props} />,
                          ol: ({node, ...props}) => <ol style={{ paddingLeft: '18px', marginBottom: '6px' }} {...props} />,
                          li: ({node, ...props}) => <li style={{ marginBottom: '2px' }} {...props} />
                        }}
                      >
                        {mentorReview.review}
                      </ReactMarkdown>
                      {/* 流式打字机闪烁光标 */}
                      {isMentorStreaming && (
                        <span style={{
                          display: 'inline-block',
                          width: '7px',
                          height: '14px',
                          background: 'var(--wb-accent-primary)',
                          marginLeft: '2px',
                          verticalAlign: 'middle',
                          animation: 'pulse 1s infinite'
                        }} />
                      )}
                    </div>

                    {/* 智能追问与多模态交互栏 */}
                    <div style={{
                      marginTop: '14px',
                      paddingTop: '12px',
                      borderTop: '1px solid var(--wb-border-subtle)'
                    }}>
                      {/* 快速追问预设 Tag */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>快捷诊断:</span>
                        {[
                          '⚡ 性能与超时优化',
                          '🛡️ 异常与边界防御',
                          '🔄 异步并发改造',
                          '🎯 关卡满分重构'
                        ].map(tag => (
                          <button
                            key={tag}
                            onClick={() => handleAskMentor(tag)}
                            disabled={isMentorStreaming}
                            className="wb-btn-ghost"
                            style={{
                              fontSize: '10.5px',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              background: 'var(--wb-bg-hover)',
                              border: '1px solid var(--wb-border-subtle)'
                            }}
                          >
                            {tag}
                          </button>
                        ))}
                      </div>

                      {/* 自定义提问输入框与多模态截图附件 */}
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          if (mentorQuestion.trim()) handleAskMentor(mentorQuestion.trim());
                        }}
                        style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
                      >
                        {/* 划词重点聚焦与多轮对话指示微胶囊 */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                          {selectedCode ? (
                            <div style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '3px 8px',
                              background: 'rgba(59, 130, 246, 0.15)',
                              border: '1px solid rgba(59, 130, 246, 0.35)',
                              borderRadius: '4px',
                              fontSize: '11px',
                              color: '#93c5fd'
                            }}>
                              <Sparkles size={11} color="#60a5fa" />
                              <span>已锁定选区 ({selectedCode.split('\n').length} 行代码聚焦)</span>
                              <button
                                type="button"
                                onClick={() => {
                                  setSelectedCode('');
                                  setSelectionWidgetPos(null);
                                }}
                                style={{ background: 'none', border: 'none', color: '#93c5fd', cursor: 'pointer', padding: 0 }}
                                title="取消选区锁定"
                              >
                                <X size={11} />
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>
                              💡 提示：在编辑器中划词选中局部代码可进行定向解答
                            </span>
                          )}

                          {mentorChatHistory.length > 0 && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>
                                连贯对话: {Math.floor(mentorChatHistory.length / 2)} 轮上下文
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  setMentorChatHistory([]);
                                  showToast('已清空导师多轮对话上下文');
                                }}
                                className="wb-btn-ghost"
                                style={{ fontSize: '10px', padding: '1px 5px' }}
                                title="重置对话上下文"
                              >
                                新对话
                              </button>
                            </div>
                          )}
                        </div>

                        {mentorImage && (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '4px 8px',
                            background: 'rgba(59, 130, 246, 0.15)',
                            border: '1px solid rgba(59, 130, 246, 0.3)',
                            borderRadius: '6px',
                            width: 'fit-content'
                          }}>
                            <Image size={12} color="#60a5fa" />
                            <span style={{ fontSize: '11px', color: '#93c5fd' }}>已附加 1 张多模态排障截图</span>
                            <button
                              type="button"
                              onClick={() => setMentorImage(null)}
                              style={{ background: 'none', border: 'none', color: '#93c5fd', cursor: 'pointer', padding: 0 }}
                            >
                              <X size={12} />
                            </button>
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: '8px' }}>
                          <input
                            type="text"
                            value={mentorQuestion}
                            onChange={(e) => setMentorQuestion(e.target.value)}
                            placeholder="向 AI 导师提问具体困惑，例如：如何避免大模型生成超时？如何改造为异步并发？"
                            disabled={isMentorStreaming}
                            style={{
                              flex: 1,
                              background: 'var(--wb-bg-root)',
                              border: '1px solid var(--wb-border-subtle)',
                              borderRadius: '6px',
                              padding: '6px 10px',
                              fontSize: '12px',
                              color: 'var(--wb-text-bright)',
                              outline: 'none'
                            }}
                          />

                          {/* 多模态报错截图上传按钮 */}
                          <label
                            className="wb-btn-ghost"
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 10px',
                              cursor: 'pointer',
                              fontSize: '11.5px'
                            }}
                            title="上传报错截图或拓扑图，启用多模态视觉协同排查"
                          >
                            <Image size={13} />
                            <span>截图</span>
                            <input
                              type="file"
                              accept="image/*"
                              style={{ display: 'none' }}
                              onChange={handleImageUpload}
                            />
                          </label>

                          <button
                            type="submit"
                            disabled={isMentorStreaming || !mentorQuestion.trim()}
                            className="wb-btn-ghost"
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px',
                              background: 'var(--wb-accent-subtle)',
                              color: '#ffffff',
                              border: 'none',
                              padding: '6px 12px',
                              borderRadius: '6px',
                              fontSize: '11.5px',
                              cursor: (isMentorStreaming || !mentorQuestion.trim()) ? 'not-allowed' : 'pointer'
                            }}
                          >
                            <Send size={12} />
                            <span>{isMentorStreaming ? '推理中...' : '深度追问'}</span>
                          </button>
                        </div>
                      </form>
                    </div>
                  </div>
                ) : (
                  <div style={{
                    padding: '24px 16px',
                    textAlign: 'center',
                    background: 'var(--wb-bg-subtle)',
                    borderRadius: '8px',
                    border: '1px dashed var(--wb-border-subtle)'
                  }}>
                    <div style={{ fontSize: '12.5px', color: 'var(--wb-text-sub)', marginBottom: '8px' }}>
                      尚未生成本关诊断报告。
                    </div>
                    <button
                      onClick={() => handleAskMentor()}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'var(--wb-accent-subtle)',
                        color: '#ffffff',
                        border: 'none',
                        padding: '5px 14px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      <Sparkles size={13} />
                      <span>唤醒 AI 伴学导师进行深度诊断</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
