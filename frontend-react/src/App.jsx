import React, { useState, useEffect } from 'react';
import HeaderBar from './components/Workbench/HeaderBar';
import CurriculumNav from './components/Workbench/CurriculumNav';
import MissionGuide from './components/Workbench/MissionGuide';
import CodeConsole from './components/Workbench/CodeConsole';
import DashboardView from './components/Workbench/DashboardView';
import CommandPalette from './components/Workbench/CommandPalette';
import CompetencyReportModal from './components/Workbench/CompetencyReportModal';
import UserRoleGovernanceModal from './components/Workbench/UserRoleGovernanceModal';
import LoginModal from './components/Workbench/LoginModal';
import EnterpriseLoginPage from './components/Workbench/EnterpriseLoginPage';
import KnowledgeManagerModal from './components/Workbench/KnowledgeManagerModal';
import './index.css';

// 24 阶段离线备用数据 (开箱即用保障)
// 规范化章节标题工具：彻底剥离章节目录名称前头的数字、代号与连字符，如 "17-transformers-basics · " 或 "01. "
export function formatPhaseTitle(title) {
  if (!title) return '';
  return title
    .replace(/^\d+[-_][a-zA-Z0-9\-_]+\s*[·:：\-—]\s*/, '')
    .replace(/^\d+([-_][a-zA-Z0-9]+)?[\.、\-\s]+\s*/, '')
    .trim();
}

const FALLBACK_PHASES = [
  { id: '01-prompt-engineering', order: 1, title: 'Prompt 工程基础与进阶', slug: 'prompt-engineering', description: '系统提示词、思维链 CoT、少样本 Few-Shot 与提示词工程化', tags: ['Prompt', 'NLP'], difficulty: 'Beginner' },
  { id: '02-function-calling', order: 2, title: 'Function Calling 工具调用', slug: 'function-calling', description: '结构化输出、函数参数校验与外部 API 自动化调用', tags: ['Tool', 'API'], difficulty: 'Beginner' },
  { id: '03-mcp', order: 3, title: 'MCP 模型上下文协议实战', slug: 'mcp', description: 'Anthropic Model Context Protocol 协议与跨进程通信', tags: ['MCP', 'Protocol'], difficulty: 'Intermediate' },
  { id: '04-rag', order: 4, title: 'RAG 知识库检索增强生成', slug: 'rag', description: '向量数据库 Chroma、分块策略、混合重排与防幻觉检验', tags: ['RAG', 'VectorDB'], difficulty: 'Intermediate' },
  { id: '05-embedding', order: 5, title: 'Embedding 向量化与语义相似度', slug: 'embedding', description: '稠密与稀疏向量、余弦相似度计算与语义聚类', tags: ['NLP', 'Vector'], difficulty: 'Beginner' },
  { id: '06-agent-basics', order: 6, title: 'LangGraph 循环状态 Agent', slug: 'agent-basics', description: 'StateGraph 编排、条件边路由与工具节点循环执行', tags: ['Agent', 'LangGraph'], difficulty: 'Intermediate' },
  { id: '07-advanced-memory', order: 7, title: 'Agent 深度长短期记忆架构', slug: 'advanced-memory', description: '长短期记忆、会话摘要压缩、用户画像与认知状态', tags: ['Memory', 'Agent'], difficulty: 'Intermediate' },
  { id: '08-multimodal', order: 8, title: '多模态理解与图文交互', slug: 'multimodal', description: '视觉大模型、图片分析、语音交互与文档 OCR', tags: ['Vision', 'Audio'], difficulty: 'Intermediate' },
  { id: '09-evaluation', order: 9, title: 'Ragas 评测与 LangSmith 观测', slug: 'evaluation', description: '忠实度、答案相关性量化评估与全链路 Trace 追踪', tags: ['Eval', 'Tracing'], difficulty: 'Intermediate' },
  { id: '10-production', order: 10, title: '生产级实战与高并发网关', slug: 'production', description: '流式输出、HITL 人机协同审批与语义缓存优化', tags: ['Prod', 'FastAPI'], difficulty: 'Advanced' },
  { id: '11-python-advanced', order: 11, title: 'Python 高级特性与并发编程', slug: 'python-advanced', description: '异步 asyncio、元编程、生成器与底层优化', tags: ['Python', 'Async'], difficulty: 'Intermediate' },
  { id: '12-fastapi-advanced', order: 12, title: 'FastAPI 高性能接口设计', slug: 'fastapi-advanced', description: '依赖注入、生命周期 lifespan 与中间件安全控制', tags: ['Backend', 'FastAPI'], difficulty: 'Intermediate' },
  { id: '13-sqlalchemy-advanced', order: 13, title: '异步 SQLAlchemy 与数据库治理', slug: 'sqlalchemy-advanced', description: '连接池优化、异步迁移与模型映射最佳实践', tags: ['Database', 'ORM'], difficulty: 'Intermediate' },
  { id: '14-celery-advanced', order: 14, title: 'Celery 分布式任务队列', slug: 'celery-advanced', description: 'Redis 消息代理、异步解耦与任务超时重试机制', tags: ['Queue', 'Distributed'], difficulty: 'Intermediate' },
  { id: '15-agent-architecture', order: 15, title: '企业级 Agent 架构深度解构', slug: 'agent-architecture', description: 'Plan-and-Solve、ReAct 范式演进与任务分解', tags: ['Agent', 'Architecture'], difficulty: 'Advanced' },
  { id: '16-face-recognition', order: 16, title: '计算机视觉与人脸特征提取', slug: 'face-recognition', description: 'OpenCV 与深度特征比对、人脸活体检测实战', tags: ['CV', 'Vision'], difficulty: 'Intermediate' },
  { id: '17-transformers-basics', order: 17, title: 'Transformers 核心架构与注意力机制', slug: 'transformers-basics', description: 'Self-Attention 计算、Positional Encoding 与前向传播', tags: ['Transformer', 'Math'], difficulty: 'Advanced' },
  { id: '18-inference-serving', order: 18, title: '大模型推理加速与 vLLM 部署', slug: 'inference-serving', description: 'PagedAttention、KV Cache 显存优化与流式并发服务', tags: ['Serving', 'vLLM'], difficulty: 'Advanced' },
  { id: '19-model-finetuning', order: 19, title: 'LoRA / QLoRA 领域微调实战', slug: 'model-finetuning', description: 'PEFT 参数高效微调、量化加载与指令微调数据集构建', tags: ['Finetune', 'LoRA'], difficulty: 'Advanced' },
  { id: '20-graph-rag', order: 20, title: '知识图谱增强检索与拓扑推理 (Graph RAG)', slug: 'graph-rag', description: '实体关系抽取、图检索与语义互联增强', tags: ['Graph', 'RAG'], difficulty: 'Advanced' },
  { id: '21-agent-frameworks', order: 21, title: '工业级智能体框架演进 (LangGraph / AutoGen)', slug: 'agent-frameworks', description: '多智能体对话、角色分工与群聊编排模式', tags: ['Multi-Agent', 'AutoGen'], difficulty: 'Advanced' },
  { id: '22-multi-agent-scale', order: 22, title: '大规模多智能体编排与分布式调度', slug: 'multi-agent-scale', description: '层次化拓扑、冲突裁决与任务容错编排', tags: ['Scale', 'Multi-Agent'], difficulty: 'Advanced' },
  { id: '23-ai-security', order: 23, title: 'AI 安全风控与提示词注入防御', slug: 'ai-security', description: '红蓝对抗、越狱防御、敏感信息脱敏与护栏策略', tags: ['Security', 'Safety'], difficulty: 'Advanced' },
  { id: '24-edge-ai', order: 24, title: '端侧 AI 与边缘设备本地推理加速 (Apple MLX)', slug: 'edge-ai', description: 'Apple MLX、统一内存优化与端侧极速推理落地', tags: ['Edge', 'Mobile'], difficulty: 'Advanced' }
];

export default function App() {
  const [currentMode, setCurrentMode] = useState('workbench'); // 'workbench' | 'dashboard'
  const [phases, setPhases] = useState(FALLBACK_PHASES);
  const [activePhaseId, setActivePhaseId] = useState('01-prompt-engineering');
  const [phaseDetail, setPhaseDetail] = useState(null);
  const [completedPhases, setCompletedPhases] = useState({});
  const [sandboxReady, setSandboxReady] = useState(true);

  // 多租户治理与 RBAC 状态
  const [currentTenant, setCurrentTenant] = useState({
    tenant_id: 'tenant_enterprise_core',
    tenant_name: '企业核心智算中心 (主租户/最高配)',
    monthly_token_budget: 2000000,
    tokens_consumed: 142500,
    tokens_remaining: 1857500,
    is_exhausted: false
  });
  const [currentUser, setCurrentUser] = useState({
    user_id: 'usr_superadmin_01',
    username: 'admin',
    role: 'admin',
    display_name: '超级管理员 (最高权限)'
  });
  const [tenantsList, setTenantsList] = useState([]);
  const [isGovernanceOpen, setIsGovernanceOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  // 强制企业鉴权状态守卫 (未登录拦截)
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    try {
      return Boolean(localStorage.getItem('agentforge_jwt_token'));
    } catch {
      return false;
    }
  });

  const handleLogout = () => {
    try {
      localStorage.removeItem('agentforge_jwt_token');
    } catch (e) {
      console.warn('Clear token error:', e);
    }
    setIsAuthenticated(false);
  };

  const handleLoginSuccess = (authData) => {
    if (authData?.user) setCurrentUser(authData.user);
    if (authData?.tenant) setCurrentTenant(authData.tenant);
    setIsAuthenticated(true);
    fetchTenantContext();
  };

  // 面板折叠状态控制 (极大减轻视觉疲劳，让出大屏呼吸感)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [guideCollapsed, setGuideCollapsed] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);

  // 多人群主题切换 (曜石黑、北欧灰蓝、墨玉绿、纸墨白)
  const [currentTheme, setCurrentTheme] = useState('obsidian');

  // 当前手动选择并载入编辑器的外部实战脚本文件 (null 表示主通关 solution.py)
  const [activeCodeFile, setActiveCodeFile] = useState(null);


  // 闯关进阶模式 (遵循前置依赖树) VS 自由探索模式 (全量开放)
  const [isChallengeMode, setIsChallengeMode] = useState(() => {
    try {
      return localStorage.getItem('ai_learning_challenge_mode') !== 'false';
    } catch {
      return true;
    }
  });

  const handleToggleChallengeMode = () => {
    setIsChallengeMode(prev => {
      const next = !prev;
      try {
        localStorage.setItem('ai_learning_challenge_mode', String(next));
      } catch (e) {
        console.warn('Save challenge mode failed:', e);
      }
      return next;
    });
  };

  // 判断指定关卡是否满足解锁条件
  const isPhaseUnlocked = (targetPhaseId) => {
    if (!isChallengeMode) return true;
    const p = phases.find(x => x.id === targetPhaseId);
    if (!p) return true;
    if (p.order === 1 || p.id === '01-prompt-engineering') return true;

    const prereqs = p.prerequisites || [];
    if (prereqs.length === 0) {
      const prev = phases.find(x => x.order === p.order - 1);
      return prev ? Boolean(completedPhases[prev.id]?.passed || completedPhases[prev.id]) : true;
    }
    return prereqs.every(reqId => Boolean(completedPhases[reqId]?.passed || completedPhases[reqId]));
  };

  const applyTheme = (themeId) => {
    setCurrentTheme(themeId);
    document.body.classList.remove('theme-obsidian', 'theme-nordic', 'theme-sepia', 'theme-paper');
    document.body.classList.add(`theme-${themeId}`);
    try {
      localStorage.setItem('ai_learning_theme', themeId);
    } catch (e) {
      console.warn('Save theme failed:', e);
    }
  };

  useEffect(() => {
    document.body.classList.add('dark-workbench');
    const savedTheme = localStorage.getItem('ai_learning_theme') || 'obsidian';
    applyTheme(savedTheme);

    try {
      const saved = localStorage.getItem('ai_learning_completed_phases');
      if (saved) {
        setCompletedPhases(JSON.parse(saved));
      }
    } catch (e) {
      console.warn('Load saved progress failed:', e);
    }
  }, []);

  // 全局 ⌘K 键盘快捷键监听
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 多租户鉴权与配额初始化 (同时拉取云端 SQLite 用户进度)
  const fetchTenantContext = async () => {
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      if (!token) {
        setIsAuthenticated(false);
        return;
      }
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const meRes = await fetch('/api/v1/auth/me', { headers });
      if (!meRes.ok) {
        localStorage.removeItem('agentforge_jwt_token');
        setIsAuthenticated(false);
        return;
      }
      const meData = await meRes.json();
      if (meData.status === 'success') {
        if (meData.user) setCurrentUser(meData.user);
        if (meData.tenant) setCurrentTenant(meData.tenant);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('agentforge_jwt_token');
        setIsAuthenticated(false);
      }

      const tenantsRes = await fetch('/api/v1/tenants');
      const tenantsData = await tenantsRes.json();
      if (tenantsData.status === 'success' && tenantsData.tenants) {
        setTenantsList(tenantsData.tenants);
      }

      // 拉取该用户在 SQLite 中的云端持久化通关进度
      try {
        const progRes = await fetch('/api/v1/curriculum/user-progress', { headers });
        if (progRes.ok) {
          const progData = await progRes.json();
          if (progData.status === 'success' && progData.progress) {
            setCompletedPhases(prev => {
              const merged = { ...prev, ...progData.progress };
              try {
                localStorage.setItem('ai_learning_completed_phases', JSON.stringify(merged));
              } catch {}
              return merged;
            });
          }
        }
      } catch (errProg) {
        console.warn('Sync cloud user progress error:', errProg);
      }
    } catch (e) {
      console.warn('Load tenant context error:', e);
    }
  };

  useEffect(() => {
    fetchTenantContext();
  }, []);

  const handleSwitchTenant = async (targetTenantId) => {
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch('/api/v1/tenants/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': targetTenantId
        },
        body: JSON.stringify({ target_tenant_id: targetTenantId })
      });
      const data = await res.json();
      if (data.status === 'success') {
        if (data.token) localStorage.setItem('agentforge_jwt_token', data.token);
        if (data.tenant) setCurrentTenant(data.tenant);
        fetchTenantContext();
      }
    } catch (e) {
      console.error('Switch tenant failed:', e);
    }
  };

  const handleUpdateTenantQuota = (newQuota) => {
    if (newQuota) {
      setCurrentTenant(prev => ({ ...prev, ...newQuota }));
    }
  };

  const handleResetTenantQuota = async (tenantId, newConsumed = 0, addBudget = 0) => {
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch('/api/v1/tenants/reset-quota', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': tenantId
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          new_consumed: newConsumed,
          add_budget: addBudget
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        if (data.tenant && currentTenant?.tenant_id === tenantId) {
          setCurrentTenant(data.tenant);
        }
        await fetchTenantContext();
        return { success: true, message: data.message, tenant: data.tenant };
      } else {
        return { success: false, message: data.detail || '重置失败' };
      }
    } catch (e) {
      return { success: false, message: e.message };
    }
  };

  // 从后端获取 24 阶段列表
  useEffect(() => {
    fetch('/api/v1/curriculum/phases')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.phases?.length > 0) {
          const cleanedPhases = data.phases.map(p => ({
            ...p,
            title: formatPhaseTitle(p.title)
          }));
          setPhases(cleanedPhases);
          setSandboxReady(true);
        }
      })
      .catch(() => {
        setSandboxReady(false);
      });
  }, []);

  // 当激活关卡变化时获取详情
  useEffect(() => {
    if (!activePhaseId) return;
    setActiveCodeFile(null); // 重置外部脚本选中状态，恢复主通关代码视图

    fetch(`/api/v1/curriculum/phases/${activePhaseId}`)
      .then(res => res.json())
      .then(data => {
        if ((data.code === 200 || data.status === 'success' || data.data) && data.data) {
          setPhaseDetail({
            ...data.data,
            title: formatPhaseTitle(data.data.title)
          });
        } else {
          console.warn('Phase detail load returned invalid data:', data);
        }
      })
      .catch(() => {
        const p = phases.find(x => x.id === activePhaseId);
        setPhaseDetail({
          id: activePhaseId,
          guide_markdown: `# ${p?.title || '实验关卡'}\n\n欢迎进入当前实战阶段。\n\n## 知识点总结\n- 掌握核心接口设计与数据流转\n- 规避常见边界异常与性能瓶颈`,
          starter_code: `# 实战关卡: ${activePhaseId}\n\ndef solution():\n    print("欢迎来到 AI Learning Lab 实战工作台")\n    return True\n\nif __name__ == "__main__":\n    solution()\n`,
          test_code: `import unittest\n\nclass TestLab(unittest.TestCase):\n    def test_run(self):\n        self.assertTrue(True)\n`,
          checklist: [
            { text: '阅读并理解当前阶段指导手册', done: true },
            { text: '在右侧编辑区调试核心代码', done: false },
            { text: '点击【验证通关】完成自动化评测', done: false }
          ]
        });
      });
  }, [activePhaseId, phases]);

  const handlePassPhase = (phaseId, meta = {}) => {
    const p = phases.find(x => x.id === phaseId);
    const baseXP = p ? (p.difficulty === 'Advanced' ? 240 : p.difficulty === 'Intermediate' ? 140 : 80) : 100;
    setCompletedPhases(prev => {
      const prevData = typeof prev[phaseId] === 'object' ? prev[phaseId] : {};
      const updated = {
        ...prev,
        [phaseId]: {
          passed: true,
          completedAt: Date.now(),
          xpEarned: baseXP,
          ...prevData,
          ...meta
        }
      };
      try {
        localStorage.setItem('ai_learning_completed_phases', JSON.stringify(updated));
      } catch (e) {
        console.warn('Save progress failed:', e);
      }
      return updated;
    });

    // 触发云端 SQLite 物理双写同步
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      fetch('/api/v1/curriculum/user-progress', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          phase_id: phaseId,
          passed: true,
          xp_earned: baseXP,
          saved_code: meta.savedCode || '',
          execution_metrics: {
            execution_time_ms: meta.execution_time_ms || 0,
            passedAt: Date.now()
          }
        })
      }).catch(err => console.warn('Cloud sync background failed:', err));
    } catch {}
  };

  // 一键切换 Zen 模式 (全屏纯代码专注)
  const handleToggleZen = () => {
    if (sidebarCollapsed && guideCollapsed) {
      setSidebarCollapsed(false);
      setGuideCollapsed(false);
    } else {
      setSidebarCollapsed(true);
      setGuideCollapsed(true);
    }
  };

  const completedCount = Object.keys(completedPhases).filter(k => completedPhases[k]).length;
  const currentPhaseObj = phases.find(p => p.id === activePhaseId);

  // 强制企业鉴权守卫：若未登录则全屏展示登录大屏，并记录登录流水
  if (!isAuthenticated) {
    return (
      <EnterpriseLoginPage
        onLoginSuccess={handleLoginSuccess}
      />
    );
  }

  return (
    <div className="wb-layout">
      {/* 顶部极简 Header (支持多租户与 RBAC 实时管控) */}
      <HeaderBar
        completedCount={completedCount}
        totalPhases={phases.length}
        sandboxReady={sandboxReady}
        currentMode={currentMode}
        sidebarCollapsed={sidebarCollapsed}
        guideCollapsed={guideCollapsed}
        currentTheme={currentTheme}
        currentTenant={currentTenant}
        currentUser={currentUser}
        tenantsList={tenantsList}
        onSwitchTenant={handleSwitchTenant}
        onResetTenantQuota={handleResetTenantQuota}
        onOpenGovernance={() => setIsGovernanceOpen(true)}
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        onOpenLogin={() => setIsLoginOpen(true)}
        onLogout={handleLogout}
        onSelectTheme={applyTheme}
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        onToggleGuide={() => setGuideCollapsed(!guideCollapsed)}
        onToggleZen={handleToggleZen}
        setMode={setCurrentMode}
        onOpenSearch={() => setIsSearchOpen(true)}
        onOpenReport={() => setIsReportOpen(true)}
      />

      {/* 工作台与概览切换 */}
      {currentMode === 'workbench' ? (
        <div className="wb-body">
          {/* 左栏：轻量关卡路线列表 (支持折叠与前置锁定) */}
          <CurriculumNav
            phases={phases}
            activePhaseId={activePhaseId}
            completedPhases={completedPhases}
            isChallengeMode={isChallengeMode}
            isCollapsed={sidebarCollapsed}
            isPhaseUnlocked={isPhaseUnlocked}
            onToggleCollapse={() => setSidebarCollapsed(true)}
            onToggleChallengeMode={handleToggleChallengeMode}
            onSelectPhase={(id) => setActivePhaseId(id)}
          />

          {/* 中栏：实验指南 (支持折叠) */}
          <MissionGuide
            phaseDetail={phaseDetail}
            activePhaseTitle={currentPhaseObj?.title || ''}
            isCollapsed={guideCollapsed}
            codeFiles={phaseDetail?.code_files || []}
            activeCodeFile={activeCodeFile}
            onSelectCodeFile={setActiveCodeFile}
            onToggleCollapse={() => setGuideCollapsed(true)}
            onLoadStarterCode={(code) => {
              if (phaseDetail) {
                setPhaseDetail({ ...phaseDetail, starter_code: code });
              }
            }}
          />

          {/* 右栏：极简 Monaco 实战沙箱控制台 (主题联动) */}
          <CodeConsole
            phaseId={activePhaseId}
            starterCode={phaseDetail?.starter_code || ''}
            solutionCode={phaseDetail?.solution_code || ''}
            solutionSource={phaseDetail?.solution_source || ''}
            solutionDoc={phaseDetail?.solution_doc || ''}
            starterSource={phaseDetail?.starter_source || ''}
            passedHistory={completedPhases[activePhaseId]}
            testCode={phaseDetail?.test_code || ''}
            currentTheme={currentTheme}
            phases={phases}
            codeFiles={phaseDetail?.code_files || []}
            activeCodeFile={activeCodeFile}
            onSelectCodeFile={setActiveCodeFile}
            currentTenant={currentTenant}
            currentUser={currentUser}
            onUpdateTenantQuota={handleUpdateTenantQuota}
            isChallengeMode={isChallengeMode}
            isUnlocked={isPhaseUnlocked(activePhaseId)}
            onPassPhase={handlePassPhase}
            onNavigatePhase={(id) => setActivePhaseId(id)}
            onToggleChallengeMode={handleToggleChallengeMode}
          />
        </div>
      ) : (
        /* 全景概览雷达 */
        <DashboardView
          phases={phases}
          completedPhases={completedPhases}
          isChallengeMode={isChallengeMode}
          isPhaseUnlocked={isPhaseUnlocked}
          onSelectPhase={(id) => setActivePhaseId(id)}
          onSwitchToWorkbench={() => setCurrentMode('workbench')}
          onOpenReport={() => setIsReportOpen(true)}
        />
      )}

      {/* 全局 ⌘K 快速命令与关卡跳转弹窗 */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        phases={phases}
        completedPhases={completedPhases}
        onSelectPhase={(id) => setActivePhaseId(id)}
      />

      {/* 学员学习能力诊断报告弹窗 */}
      <CompetencyReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        phases={phases}
        completedPhases={completedPhases}
      />

      {/* 多租户 RBAC 权限与用户维护弹窗 */}
      <UserRoleGovernanceModal
        isOpen={isGovernanceOpen}
        onClose={() => setIsGovernanceOpen(false)}
        currentTenant={currentTenant}
        currentUser={currentUser}
        onUpdateTenantQuota={handleUpdateTenantQuota}
        onSwitchTenant={handleSwitchTenant}
      />

      {/* 企业私有知识库中心弹窗 */}
      <KnowledgeManagerModal
        isOpen={isKnowledgeOpen}
        onClose={() => setIsKnowledgeOpen(false)}
      />

      {/* 身份切换与登录弹窗 */}
      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        currentTenantId={currentTenant?.tenant_id}
        onLoginSuccess={(authData) => {
          if (authData.user) setCurrentUser(authData.user);
          if (authData.tenant) setCurrentTenant(authData.tenant);
          fetchTenantContext();
        }}
      />
    </div>
  );
}
