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
  // 🟢 初级阶段 (Beginner, 1 - 6)
  { id: '01-prompt-engineering', order: 1, title: '提示词工程核心技术与框架', slug: 'prompt-engineering', description: '系统提示词、思维链 CoT、少样本 Few-Shot 与工业级提示词工程化', tags: ['Prompt', 'NLP'], difficulty: 'Beginner' },
  { id: '02-function-calling', order: 2, title: '函数调用基础与数据验证', slug: 'function-calling', description: 'JSON Schema 结构化声明、Pydantic 参数校验与工具安全路由分发', tags: ['Tool', 'API'], difficulty: 'Beginner' },
  { id: '03-mcp', order: 3, title: '学习 MCP 协议核心概念与服务端开发', slug: 'mcp', description: 'Anthropic Model Context Protocol 协议、跨进程标准资源暴露与服务端实现', tags: ['MCP', 'Protocol'], difficulty: 'Beginner' },
  { id: '05-embedding', order: 4, title: '文本向量化、空间几何与语义相似度算法', slug: 'embedding', description: '稠密与稀疏向量表征、余弦相似度几何计算与高维语义投影', tags: ['NLP', 'Vector'], difficulty: 'Beginner' },
  { id: '04-rag', order: 5, title: 'RAG 检索增强生成 · 深度学习与实战', slug: 'rag', description: '文档切片清洗、向量数据库 Chroma/FAISS 存储与 Top-K 上下文组装问答', tags: ['RAG', 'VectorDB'], difficulty: 'Beginner' },
  { id: '11-python-advanced', order: 6, title: 'Python 高级特性与高性能编程', slug: 'python-advanced', description: '异步 asyncio 协程并发、dataclass 数据类、生成器与企业级类型注解', tags: ['Python', 'Async'], difficulty: 'Beginner' },

  // 🟡 中级阶段 (Intermediate, 7 - 17)
  { id: '12-fastapi-advanced', order: 7, title: '大模型高性能 API 网关与 SSE 流式输出', slug: 'fastapi-advanced', description: '依赖注入、Server-Sent Events 打字机流式长连接与异步高并发网关', tags: ['Backend', 'FastAPI'], difficulty: 'Intermediate' },
  { id: '13-sqlalchemy-advanced', order: 8, title: '智能体状态持久化与用户记忆资产', slug: 'sqlalchemy-advanced', description: '异步 SQLAlchemy 状态流转、用户会话画像与认知资产持久化存储', tags: ['Database', 'ORM'], difficulty: 'Intermediate' },
  { id: '14-celery-advanced', order: 9, title: '大模型长耗时任务解耦与多 Agent 分布式编排', slug: 'celery-advanced', description: 'Redis 消息队列、后台削峰填谷、异步长任务解耦与分布式作业编排', tags: ['Queue', 'Distributed'], difficulty: 'Intermediate' },
  { id: '06-agent-basics', order: 10, title: 'LangGraph 智能体基础与循环决策', slug: 'agent-basics', description: '基于 StateGraph 的有状态图编排、条件边路由、工具节点与自主决策循环', tags: ['Agent', 'LangGraph'], difficulty: 'Intermediate' },
  { id: '07-advanced-memory', order: 11, title: '智能体深度记忆与长效认知架构', slug: 'advanced-memory', description: '短期滑动窗口、会话摘要压缩、长效用户画像与跨会话实体认知记忆', tags: ['Memory', 'Agent'], difficulty: 'Intermediate' },
  { id: '26-hybrid-search-rerank', order: 12, title: '工业级混合检索与重排工程 (Hybrid Search & Reranking)', slug: 'hybrid-search-rerank', description: 'Dense 语义向量 + Sparse BM25 词法混合召回、RRF 倒排融合与 Cross-Encoder 深度重排', tags: ['RAG', 'Rerank'], difficulty: 'Intermediate' },
  { id: '08-multimodal', order: 13, title: '多模态与视觉识别探索', slug: 'multimodal', description: '视觉大模型、多模态图表识别、文档复杂版面 OCR 与跨模态对齐推理', tags: ['Vision', 'Audio'], difficulty: 'Intermediate' },
  { id: '21-agent-frameworks', order: 14, title: '工业级智能体框架演进 (LangGraph / AutoGen / CrewAI)', slug: 'agent-frameworks', description: '主流生产级智能体框架深度横向测评、选型对比与角色分工群聊协作', tags: ['Multi-Agent', 'AutoGen'], difficulty: 'Intermediate' },
  { id: '09-evaluation', order: 15, title: 'RAGAS 自动化评估与全链路评测', slug: 'evaluation', description: '忠实度、答案相关度、上下文召回率量化评估与 LangSmith 全链路 Trace 追踪', tags: ['Eval', 'Tracing'], difficulty: 'Intermediate' },
  { id: '10-production', order: 16, title: '端到端生产级智能体与人机协同', slug: 'production', description: '生产环境熔断降级、语义缓存优化与 Human-in-the-loop 人机回环协同审批', tags: ['Prod', 'HITL'], difficulty: 'Intermediate' },
  { id: '15-agent-architecture', order: 17, title: '企业级全栈 Agent 架构协同实战', slug: 'agent-architecture', description: 'Plan-and-Solve、ReAct 范式演进、前后端打通与多租户权限隔离实战', tags: ['Agent', 'Architecture'], difficulty: 'Intermediate' },

  // 🔴 高级阶段 (Advanced, 18 - 26)
  { id: '16-face-recognition', order: 18, title: '生产级人脸识别架构', slug: 'face-recognition', description: '计算机视觉深度特征提取、特征向量比对与高可靠人脸核身工程', tags: ['CV', 'Vision'], difficulty: 'Advanced' },
  { id: '17-transformers-basics', order: 19, title: 'Transformer 架构底座与硬件算子开发', slug: 'transformers-basics', description: '纯 PyTorch 手写 Self-Attention、Multi-Head Attention、RoPE 与 KV Cache 算子', tags: ['Transformer', 'Math'], difficulty: 'Advanced' },
  { id: '18-inference-serving', order: 20, title: '大模型高性能推理服务与高并发压测 (vLLM / Triton)', slug: 'inference-serving', description: 'PagedAttention 显存优化、连续批处理 Continuous Batching 与生产级并发吞吐压测', tags: ['Serving', 'vLLM'], difficulty: 'Advanced' },
  { id: '19-model-finetuning', order: 21, title: '领域大模型微调与 LoRA 适配 (PEFT / QLoRA)', slug: 'model-finetuning', description: 'PEFT 参数高效微调、QLoRA 4-bit 量化加载与垂直领域微调语料清洗飞轮', tags: ['Finetune', 'LoRA'], difficulty: 'Advanced' },
  { id: '25-reasoning-rl', order: 22, title: '大模型后训练强化学习与长思维链推理 (GRPO & Reasoning RL)', slug: 'reasoning-rl', description: 'DeepSeek-R1 核心的 GRPO 组相对优势算法、规则驱动多维奖励引擎与自反思推理', tags: ['RL', 'DeepSeek'], difficulty: 'Advanced' },
  { id: '20-graph-rag', order: 23, title: '知识图谱增强检索与拓扑推理 (Graph RAG)', slug: 'graph-rag', description: '图谱实体三元组抽取、拓扑关联子图检索与多跳逻辑推理增强', tags: ['Graph', 'RAG'], difficulty: 'Advanced' },
  { id: '22-multi-agent-scale', order: 24, title: '多智能体集群编排与规模化调度', slug: 'multi-agent-scale', description: '多 Agent 集群组织拓扑、动态辩论裁决与生产级分布式任务容错调度', tags: ['Scale', 'Multi-Agent'], difficulty: 'Advanced' },
  { id: '23-ai-security', order: 25, title: 'AI 安全防御、防提示词注入与沙箱隔离', slug: 'ai-security', description: '间接提示词注入攻击防御、AST 静态审查、沙箱逃逸防护与安全护栏 Guardrails', tags: ['Security', 'Safety'], difficulty: 'Advanced' },
  { id: '24-edge-ai', order: 26, title: '端侧 AI 与边缘设备本地推理加速 (Apple MLX)', slug: 'edge-ai', description: 'Apple MLX 框架、统一内存架构 (UMA) 深度优化与端侧轻量化模型毫秒级推理', tags: ['Edge', 'Mobile'], difficulty: 'Advanced' }
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
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const cached = localStorage.getItem('agentforge_cached_user');
      if (cached) return JSON.parse(cached);
    } catch {}
    return {
      user_id: 'usr_superadmin_01',
      username: 'admin',
      role: 'admin',
      display_name: '超级管理员 (最高权限)'
    };
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
      localStorage.removeItem('agentforge_cached_user');
    } catch (e) {
      console.warn('Clear token error:', e);
    }
    setIsAuthenticated(false);
  };

  const handleLoginSuccess = (authData) => {
    if (authData?.user) {
      setCurrentUser(authData.user);
      try {
        localStorage.setItem('agentforge_cached_user', JSON.stringify(authData.user));
      } catch {}
    }
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
        localStorage.removeItem('agentforge_cached_user');
        setIsAuthenticated(false);
        return;
      }
      const meData = await meRes.json();
      if (meData.status === 'success') {
        if (meData.user) {
          setCurrentUser(meData.user);
          try {
            localStorage.setItem('agentforge_cached_user', JSON.stringify(meData.user));
          } catch {}
        }
        if (meData.tenant) setCurrentTenant(meData.tenant);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('agentforge_jwt_token');
        localStorage.removeItem('agentforge_cached_user');
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
