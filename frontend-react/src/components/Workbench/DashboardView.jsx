import React, { useState } from 'react';
import { 
  Trophy, Award, Target, CheckCircle2, Flame, 
  ArrowRight, ShieldCheck, Zap, Database, BrainCircuit,
  Sparkles, Star, ChevronRight, Filter, Clock, Lock, Unlock
} from 'lucide-react';

// 六大技术领域真实划分配置与关卡映射
const DOMAIN_CONFIG = [
  {
    id: 'prompt_nlp',
    name: 'Prompt & NLP 基础',
    icon: Zap,
    description: '系统提示词、思维链 CoT、少样本 Few-shot 与提示工程分层',
    phaseIds: ['01-prompt-engineering', '02-function-calling', '05-embedding']
  },
  {
    id: 'rag_retrieval',
    name: 'RAG & 向量检索架构',
    icon: Database,
    description: 'Chroma/混合检索、动态分块、重排与 Graph RAG 融合',
    phaseIds: ['04-rag', '20-graph-rag', '08-multimodal']
  },
  {
    id: 'agent_graph',
    name: 'Agent 智能体与状态图',
    icon: BrainCircuit,
    description: 'LangGraph 循环图、长短期记忆认知、多智能体协同编排',
    phaseIds: ['03-mcp', '06-agent-basics', '07-advanced-memory', '15-agent-architecture', '21-agent-frameworks', '22-multi-agent-scale']
  },
  {
    id: 'llmops_serving',
    name: 'LLMOps 推理与微调',
    icon: Target,
    description: 'Transformers 注意力机制、vLLM 推理加速、LoRA 微调与端侧部署',
    phaseIds: ['17-transformers-basics', '18-inference-serving', '19-model-finetuning', '24-edge-ai']
  },
  {
    id: 'ai_security',
    name: 'AI 安全治理与评测',
    icon: ShieldCheck,
    description: 'Ragas 量化评估、提示词注入防御、安全护栏与红蓝对抗',
    phaseIds: ['09-evaluation', '23-ai-security']
  },
  {
    id: 'infra_backend',
    name: '高并发系统与工程基建',
    icon: Flame,
    description: 'FastAPI 依赖注入、异步 SQLAlchemy、Celery 队列、高并发网关',
    phaseIds: ['10-production', '11-python-advanced', '12-fastapi-advanced', '13-sqlalchemy-advanced', '14-celery-advanced', '16-face-recognition']
  }
];

// 六阶段位与成长阶梯模型 (大厂 AI 工程师能力对齐)
const RANKS = [
  {
    level: 1,
    title: 'AI 启蒙者',
    enTitle: 'AI Novice',
    minXp: 0,
    maxXp: 200,
    badge: '🌱 初学探索',
    color: '#94a3b8',
    nextLevelHint: '掌握基础 Prompt 规范与大模型接口交互'
  },
  {
    level: 2,
    title: '提示工程专员',
    enTitle: 'Prompt Specialist',
    minXp: 200,
    maxXp: 500,
    badge: '⚡ 提示精通',
    color: '#38bdf8',
    nextLevelHint: '攻克工具调用 (Function Calling) 与向量检索 (RAG)'
  },
  {
    level: 3,
    title: 'RAG 检索架构师',
    enTitle: 'RAG Architect',
    minXp: 500,
    maxXp: 1100,
    badge: '📚 知识检索',
    color: '#34d399',
    nextLevelHint: '攻克 LangGraph 循环 Agent 与复杂状态记忆'
  },
  {
    level: 4,
    title: 'Agent 智能体专家',
    enTitle: 'Agent Developer',
    minXp: 1100,
    maxXp: 1900,
    badge: '🤖 智能体拓扑',
    color: '#818cf8',
    nextLevelHint: '攻克 Transformers 核心算子与 vLLM 推理加速'
  },
  {
    level: 5,
    title: 'LLMOps 领域专家',
    enTitle: 'LLMOps Expert',
    minXp: 1900,
    maxXp: 2800,
    badge: '🚀 算力微调',
    color: '#f59e0b',
    nextLevelHint: '攻克多智能体大规模集群编排与全链路安全治理'
  },
  {
    level: 6,
    title: '首席 AI 架构师',
    enTitle: 'Staff AI Architect',
    minXp: 2800,
    maxXp: 4200,
    badge: '👑 殿堂架构',
    color: '#f43f5e',
    nextLevelHint: '登顶 24 关全栈图谱，具备顶级企业级 AI 战略落地能力'
  }
];

export default function DashboardView({
  phases = [],
  completedPhases = {},
  isChallengeMode = true,
  isPhaseUnlocked = () => true,
  onSelectPhase = () => {},
  onSwitchToWorkbench = () => {},
  onOpenReport = () => {}
}) {
  const [selectedDomainFilter, setSelectedDomainFilter] = useState('all');

  // 判断关卡是否通关（兼容 boolean 与对象元数据结构）
  const isPhasePassed = (phaseId) => {
    const item = completedPhases[phaseId];
    if (!item) return false;
    if (typeof item === 'boolean') return item;
    return Boolean(item.passed);
  };

  // 获取关卡基础经验值
  const getPhaseBaseXP = (p) => {
    if (p.difficulty === 'Advanced') return 240;
    if (p.difficulty === 'Intermediate') return 140;
    return 80;
  };

  // 1. 真实经验值与通关关卡计算
  let totalXP = 0;
  let maxTotalXP = 0;
  let completedCount = 0;
  const totalCount = phases.length || 24;

  phases.forEach(p => {
    const baseXP = getPhaseBaseXP(p);
    maxTotalXP += baseXP;
    if (isPhasePassed(p.id)) {
      completedCount++;
      const item = completedPhases[p.id];
      const xpEarned = (typeof item === 'object' && item.xpEarned) ? item.xpEarned : baseXP;
      totalXP += xpEarned;
    }
  });

  const progressPercent = Math.round((completedCount / totalCount) * 100);

  // 2. 匹配当前所处的职阶段位 (Rank & Level)
  let currentRank = RANKS[0];
  for (let i = RANKS.length - 1; i >= 0; i--) {
    if (totalXP >= RANKS[i].minXp) {
      currentRank = RANKS[i];
      break;
    }
  }

  const isMaxLevel = currentRank.level === RANKS.length;
  const xpInCurrentLevel = totalXP - currentRank.minXp;
  const levelCapacity = currentRank.maxXp - currentRank.minXp;
  const levelProgressPercent = isMaxLevel ? 100 : Math.min(100, Math.round((xpInCurrentLevel / levelCapacity) * 100));
  const remainingXP = isMaxLevel ? 0 : Math.max(0, currentRank.maxXp - totalXP);
  const estPhasesToNext = Math.ceil(remainingXP / 140);

  // 3. 真实多维雷达能力分析 (不再全盘虚假联动，真实统计各自领域的攻关情况)
  const domainStats = DOMAIN_CONFIG.map(domain => {
    const domainPhases = phases.filter(p => domain.phaseIds.includes(p.id));
    const countTotal = domainPhases.length || 1;
    const countDone = domainPhases.filter(p => isPhasePassed(p.id)).length;
    
    // 真实分数：根据通关占比计算
    const score = Math.round((countDone / countTotal) * 100);

    return {
      ...domain,
      countTotal,
      countDone,
      score
    };
  });

  // 4. 筛选卡片墙
  const filteredPhases = selectedDomainFilter === 'all' 
    ? phases 
    : phases.filter(p => {
        const domain = DOMAIN_CONFIG.find(d => d.id === selectedDomainFilter);
        return domain ? domain.phaseIds.includes(p.id) : true;
      });

  // 5. 寻找下一个推荐攻克的关卡 (第一个未通关的关卡)
  const nextRecommendedPhase = phases.find(p => !isPhasePassed(p.id)) || phases[0];

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '32px',
      background: 'var(--wb-bg-root)',
      color: 'var(--wb-text-bright)'
    }} className="wb-custom-scroll">
      <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
        
        {/* 顶部企业级 Bento 仪表盘 */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '20px',
          marginBottom: '32px'
        }}>
          {/* 卡片 1: 学习职阶段位与升级进度 */}
          <div style={{
            background: 'var(--wb-bg-subtle)',
            border: '1px solid var(--wb-border-subtle)',
            borderRadius: '12px',
            padding: '24px',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={18} color={currentRank.color} />
                <span style={{ fontSize: '13px', color: 'var(--wb-text-sub)', fontWeight: 600 }}>当前工程师职阶</span>
              </div>
              <span style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'var(--wb-bg-hover)',
                color: currentRank.color,
                fontWeight: 600,
                border: `1px solid ${currentRank.color}40`
              }}>
                {currentRank.badge}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '26px', fontWeight: 800, color: 'var(--wb-text-bright)' }}>
                Lv.{currentRank.level} {currentRank.title}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--wb-text-dim)', fontFamily: 'var(--wb-font-mono)' }}>
                {currentRank.enTitle}
              </span>
            </div>

            <div style={{ fontSize: '12px', color: 'var(--wb-text-dim)', marginBottom: '16px' }}>
              {isMaxLevel ? '已达成最高工程师职阶，具备顶层 AI 架构决策能力' : currentRank.nextLevelHint}
            </div>

            {/* 升级经验条 */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', marginBottom: '6px' }}>
                <span style={{ color: 'var(--wb-text-sub)' }}>
                  段位经验: <strong style={{ color: 'var(--wb-text-bright)' }}>{totalXP}</strong> / {currentRank.maxXp} XP
                </span>
                <span style={{ color: currentRank.color, fontWeight: 600 }}>
                  {levelProgressPercent}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '7px',
                borderRadius: '4px',
                background: 'var(--wb-border-subtle)',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${levelProgressPercent}%`,
                  height: '100%',
                  background: `linear-gradient(90deg, var(--wb-accent-subtle), ${currentRank.color})`,
                  transition: 'width 0.4s ease'
                }} />
              </div>
              {!isMaxLevel && (
                <div style={{ fontSize: '11px', color: 'var(--wb-text-dim)', marginTop: '8px' }}>
                  距离升级还需 <strong>{remainingXP} XP</strong> (约攻克 {estPhasesToNext} 个实战关卡)
                </div>
              )}
            </div>
          </div>

          {/* 卡片 2: 全栈 AI 掌握度与通关指标 */}
          <div style={{
            background: 'var(--wb-bg-subtle)',
            border: '1px solid var(--wb-border-subtle)',
            borderRadius: '12px',
            padding: '24px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Trophy size={18} color="var(--wb-accent-subtle)" />
                <span style={{ fontSize: '13px', color: 'var(--wb-text-sub)', fontWeight: 600 }}>全栈图谱掌握度</span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--wb-text-dim)' }}>
                {completedCount} / {totalCount} 关
              </span>
            </div>

            <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--wb-text-bright)', marginBottom: '4px' }}>
              {progressPercent}%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--wb-text-dim)', marginBottom: '16px' }}>
              累计获得实战经验 <strong>{totalXP}</strong> XP · 总关卡池 24 阶段
            </div>

            <div style={{
              width: '100%',
              height: '7px',
              borderRadius: '4px',
              background: 'var(--wb-border-subtle)',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${progressPercent}%`,
                height: '100%',
                background: 'var(--wb-accent-success)',
                transition: 'width 0.4s ease'
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--wb-text-dim)', marginTop: '8px' }}>
              <span>起步阶段</span>
              <span>架构跃迁</span>
              <span>企业级全栈</span>
            </div>
          </div>

          {/* 卡片 3: 下一步行动指引 */}
          <div style={{
            background: 'var(--wb-bg-subtle)',
            border: '1px solid var(--wb-border-subtle)',
            borderRadius: '12px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <Sparkles size={18} color="var(--wb-accent-primary)" />
                <span style={{ fontSize: '13px', color: 'var(--wb-text-sub)', fontWeight: 600 }}>推荐进阶路线</span>
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-text-bright)', marginBottom: '4px' }}>
                {nextRecommendedPhase ? nextRecommendedPhase.title : '恭喜达成全关卡通关！'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--wb-text-dim)', lineHeight: '1.5' }}>
                {nextRecommendedPhase ? nextRecommendedPhase.description : '已点亮 24 项全栈实战，欢迎继续进行深度代码重构与性能压测。'}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
              <button
                onClick={() => {
                  if (nextRecommendedPhase) {
                    onSelectPhase(nextRecommendedPhase.id);
                  }
                  onSwitchToWorkbench();
                }}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  background: 'var(--wb-accent-subtle)',
                  border: 'none',
                  color: '#ffffff',
                  padding: '9px 14px',
                  borderRadius: '6px',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background 0.15s ease'
                }}
              >
                <span>{nextRecommendedPhase ? '攻克推荐关卡' : '进入工作台'}</span>
                <ArrowRight size={14} />
              </button>

              <button
                onClick={onOpenReport}
                className="wb-btn-ghost"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  padding: '9px 12px',
                  borderColor: 'rgba(59, 130, 246, 0.4)',
                  color: 'var(--wb-accent-subtle)'
                }}
                title="生成并导出学员技术能力画像报告"
              >
                <Trophy size={13} />
                <span>生成评估报告</span>
              </button>
            </div>
          </div>
        </div>

        {/* 六大核心技术领域能力雷达 (真实数据驱动，不再全盘假联动) */}
        <div style={{
          background: 'var(--wb-bg-subtle)',
          border: '1px solid var(--wb-border-subtle)',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '32px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright)', margin: 0 }}>
                六大 AI 工程维度深度评测
              </h2>
              <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)', marginTop: '4px' }}>
                基于 24 个企业级关卡真实分类打分，精准映射您的各技术子域实战水平
              </div>
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px'
          }}>
            {domainStats.map(dim => {
              const IconComp = dim.icon;
              return (
                <div 
                  key={dim.id} 
                  onClick={() => setSelectedDomainFilter(dim.id)}
                  style={{
                    background: selectedDomainFilter === dim.id ? 'var(--wb-bg-hover)' : 'var(--wb-bg-panel)',
                    border: selectedDomainFilter === dim.id ? '1px solid var(--wb-accent-primary)' : '1px solid var(--wb-border-subtle)',
                    borderRadius: '8px',
                    padding: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <IconComp size={16} color="var(--wb-accent-subtle)" />
                      <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                        {dim.name}
                      </span>
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>
                      {dim.countDone} / {dim.countTotal} 关
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginBottom: '6px' }}>
                    <span style={{ fontSize: '20px', fontWeight: 700, color: dim.score > 0 ? 'var(--wb-text-bright)' : 'var(--wb-text-dim)' }}>
                      {dim.score}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>/ 100 分</span>
                  </div>

                  <div style={{
                    width: '100%',
                    height: '5px',
                    background: 'var(--wb-border-subtle)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                    marginBottom: '8px'
                  }}>
                    <div style={{
                      width: `${dim.score}%`,
                      height: '100%',
                      background: dim.score >= 80 ? 'var(--wb-accent-success)' : dim.score > 0 ? 'var(--wb-accent-subtle)' : 'transparent',
                      transition: 'width 0.4s ease'
                    }} />
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--wb-text-dim)', lineHeight: '1.4' }}>
                    {dim.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 全部阶段实战卡片墙 (Bento Grid + 分类筛选器) */}
        <div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '16px',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright)', margin: 0 }}>
                24 阶段实战全景图谱
              </h2>
              <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)', marginTop: '2px' }}>
                共展示 {filteredPhases.length} 项关卡
              </div>
            </div>

            {/* 领域分类切换过滤器 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setSelectedDomainFilter('all')}
                className="wb-btn-ghost"
                style={{
                  fontSize: '11.5px',
                  padding: '3px 10px',
                  borderRadius: '12px',
                  background: selectedDomainFilter === 'all' ? 'var(--wb-bg-subtle)' : 'transparent',
                  border: selectedDomainFilter === 'all' ? '1px solid var(--wb-accent-primary)' : '1px solid transparent',
                  color: selectedDomainFilter === 'all' ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)'
                }}
              >
                全部关卡 ({phases.length})
              </button>
              {DOMAIN_CONFIG.map(d => (
                <button
                  key={d.id}
                  onClick={() => setSelectedDomainFilter(d.id)}
                  className="wb-btn-ghost"
                  style={{
                    fontSize: '11.5px',
                    padding: '3px 10px',
                    borderRadius: '12px',
                    background: selectedDomainFilter === d.id ? 'var(--wb-bg-subtle)' : 'transparent',
                    border: selectedDomainFilter === d.id ? '1px solid var(--wb-accent-primary)' : '1px solid transparent',
                    color: selectedDomainFilter === d.id ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)'
                  }}
                >
                  {d.name.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '16px'
          }}>
            {filteredPhases.map(p => {
              const isDone = isPhasePassed(p.id);
              const isUnlocked = isPhaseUnlocked(p.id);
              const isLocked = !isUnlocked && isChallengeMode;
              const meta = typeof completedPhases[p.id] === 'object' ? completedPhases[p.id] : null;
              const baseXP = getPhaseBaseXP(p);

              return (
                <div
                  key={p.id}
                  onClick={() => {
                    onSelectPhase(p.id);
                    onSwitchToWorkbench();
                  }}
                  style={{
                    background: 'var(--wb-bg-subtle)',
                    border: isDone ? '1px solid var(--wb-accent-success)' : isLocked ? '1px dashed var(--wb-border-subtle)' : '1px solid var(--wb-border-subtle)',
                    borderRadius: '10px',
                    padding: '16px',
                    cursor: 'pointer',
                    transition: 'all 0.18s ease',
                    position: 'relative',
                    opacity: isLocked ? 0.65 : 1
                  }}
                  title={isLocked ? '尚未解锁，需先完成前置关卡' : p.title}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{
                      fontSize: '11px',
                      fontFamily: 'var(--wb-font-mono)',
                      color: isDone ? 'var(--wb-accent-success)' : isLocked ? 'var(--wb-text-dim)' : 'var(--wb-accent-subtle)',
                      fontWeight: 700
                    }}>
                      PHASE {String(p.order).padStart(2, '0')}
                    </span>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '10px',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: p.difficulty === 'Advanced' ? 'rgba(168, 85, 247, 0.15)' : p.difficulty === 'Intermediate' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(34, 197, 94, 0.15)',
                        color: p.difficulty === 'Advanced' ? '#c084fc' : p.difficulty === 'Intermediate' ? '#60a5fa' : '#4ade80',
                        fontWeight: 600
                      }}>
                        {p.difficulty || 'Beginner'}
                      </span>
                      {isDone ? (
                        <CheckCircle2 size={16} color="var(--wb-accent-success)" />
                      ) : isLocked ? (
                        <Lock size={14} color="var(--wb-text-dim)" />
                      ) : null}
                    </div>
                  </div>

                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-text-bright)', marginBottom: '6px' }}>
                    {p.title}
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--wb-text-sub)', lineHeight: '1.4', minHeight: '34px', marginBottom: '10px' }}>
                    {p.description}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--wb-border-subtle)', paddingTop: '10px' }}>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {p.tags?.slice(0, 2).map(t => (
                        <span key={t} style={{
                          fontSize: '10px',
                          background: 'var(--wb-bg-hover)',
                          color: 'var(--wb-text-dim)',
                          padding: '1px 5px',
                          borderRadius: '3px'
                        }}>
                          {t}
                        </span>
                      ))}
                    </div>

                    <div style={{ fontSize: '11px', color: isDone ? 'var(--wb-accent-success)' : isLocked ? 'var(--wb-text-dim)' : 'var(--wb-accent-subtle)', fontWeight: 600 }}>
                      {isDone ? `已获得 +${meta?.xpEarned || baseXP} XP` : isLocked ? `🔒 待解锁` : `+${baseXP} XP`}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
