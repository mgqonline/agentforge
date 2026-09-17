import React, { useState } from 'react';
import { 
  Trophy, Award, Target, CheckCircle2, Flame, 
  ArrowRight, ShieldCheck, Zap, Database, BrainCircuit,
  Sparkles, Star, Download, Printer, Copy, Check, X, FileText
} from 'lucide-react';

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
    phaseIds: ['03-mcp', '06-agent-basics', '07-advanced-memory', '15-agent-architecture', '20-agent-frameworks', '21-multi-agent-scale']
  },
  {
    id: 'llmops_serving',
    name: 'LLMOps 推理与微调',
    icon: Target,
    description: 'Transformers 注意力机制、vLLM 推理加速、LoRA 微调与端侧部署',
    phaseIds: ['17-transformers-basics', '18-inference-serving', '19-model-finetuning', '23-edge-ai']
  },
  {
    id: 'ai_security',
    name: 'AI 安全治理与评测',
    icon: ShieldCheck,
    description: 'Ragas 量化评估、提示词注入防御、安全护栏与红蓝对抗',
    phaseIds: ['09-evaluation', '22-ai-security']
  },
  {
    id: 'infra_backend',
    name: '高并发系统与工程基建',
    icon: Flame,
    description: 'FastAPI 依赖注入、异步 SQLAlchemy、Celery 队列、高并发网关',
    phaseIds: ['10-production', '11-python-advanced', '12-fastapi-advanced', '13-sqlalchemy-advanced', '14-celery-advanced', '16-face-recognition']
  }
];

const RANKS = [
  { level: 1, title: 'AI 启蒙者', enTitle: 'AI Novice', minXp: 0, maxXp: 200, badge: '🌱 初学探索', nextLevelHint: '掌握基础 Prompt 规范与大模型接口交互' },
  { level: 2, title: '提示工程专员', enTitle: 'Prompt Specialist', minXp: 200, maxXp: 500, badge: '⚡ 提示精通', nextLevelHint: '攻克工具调用 (Function Calling) 与向量检索 (RAG)' },
  { level: 3, title: 'RAG 检索架构师', enTitle: 'RAG Architect', minXp: 500, maxXp: 1000, badge: '📚 检索大师', nextLevelHint: '迈向 LangGraph 循环有状态智能体与长效记忆架构' },
  { level: 4, title: 'Agent 智能体架构师', enTitle: 'Agent Architect', minXp: 1000, maxXp: 1800, badge: '🤖 智能体专家', nextLevelHint: '深入大模型底层推理加速 (vLLM) 与私有微调 (LoRA)' },
  { level: 5, title: 'LLMOps 工程领航员', enTitle: 'LLMOps Navigator', minXp: 1800, maxXp: 2800, badge: '🚀 部署专家', nextLevelHint: '完成多智能体超大规模编排与企业级 AI 安全攻防护栏' },
  { level: 6, title: '全栈 AI 资深科学家', enTitle: 'AI Staff Scientist', minXp: 2800, maxXp: 99999, badge: '👑 领域宗师', nextLevelHint: '已完全掌握企业级全栈 AI 落地全景技能树！' }
];

export default function CompetencyReportModal({
  isOpen = false,
  onClose = () => {},
  phases = [],
  completedPhases = {}
}) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // 1. 基础经验值与通关统计
  const isPhasePassed = (phaseId) => {
    const item = completedPhases[phaseId];
    if (!item) return false;
    if (typeof item === 'boolean') return item;
    return Boolean(item.passed);
  };

  const getPhaseBaseXP = (p) => {
    if (p.difficulty === 'Advanced') return 240;
    if (p.difficulty === 'Intermediate') return 140;
    return 80;
  };

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

  // 2. 当前段位匹配
  let currentRank = RANKS[0];
  for (let i = RANKS.length - 1; i >= 0; i--) {
    if (totalXP >= RANKS[i].minXp) {
      currentRank = RANKS[i];
      break;
    }
  }

  // 3. 六维雷达能力得分计算
  const domainStats = DOMAIN_CONFIG.map(dim => {
    let dimEarnedXP = 0;
    let dimMaxXP = 0;
    let done = 0;

    dim.phaseIds.forEach(id => {
      const p = phases.find(x => x.id === id);
      const baseXP = p ? getPhaseBaseXP(p) : 100;
      dimMaxXP += baseXP;
      if (isPhasePassed(id)) {
        done++;
        const item = completedPhases[id];
        const earned = (typeof item === 'object' && item.xpEarned) ? item.xpEarned : baseXP;
        dimEarnedXP += earned;
      }
    });

    const score = dimMaxXP > 0 ? Math.round((dimEarnedXP / dimMaxXP) * 100) : 0;
    return {
      ...dim,
      score,
      countDone: done,
      countTotal: dim.phaseIds.length
    };
  });

  // 4. AI 伴学导师智能评语与建议
  const bestDomain = [...domainStats].sort((a, b) => b.score - a.score)[0];
  const weakestDomain = [...domainStats].sort((a, b) => a.score - b.score)[0];

  const mentorFeedback = completedCount === 0
    ? "学员刚加入实战演练，建议从【01. Prompt 工程基础】开启首战，逐步筑牢 System 提示词与工具调用的工程解耦思维。"
    : completedCount < 6
    ? `学员已在【${bestDomain.name}】展现出扎实的编码基础。目前处于初中阶爬坡期，建议紧接着完成向量检索 RAG 与状态图 Agent 模块，打通企业级 AI 开发闭环。`
    : completedCount < 18
    ? `技术画像已初具规模！在【${bestDomain.name}】（得分 ${bestDomain.score}）具备突出工程优势。当前短板为【${weakestDomain.name}】（完成 ${weakestDomain.countDone}/${weakestDomain.countTotal} 关），攻克该方向后将具备大厂资深架构师实力。`
    : `极具竞争力的全栈 AI 资深技术画像！已攻克 ${completedCount} 个工业级生产关卡，不仅精通智能体循环与大模型微调，更兼具 AI 安全风控底座。`;

  // 5. 生成报告 Markdown 文本
  const generateReportMarkdown = () => {
    return [
      `# ⚡ AgentForge · 智炼工坊 企业级学员技术能力评估报告`,
      `> 评估报告生成时间：${new Date().toLocaleString()} | 评估标准：大厂 AI 工程师能力模型 (2026)`,
      ``,
      `---`,
      ``,
      `## 一、 学员综合能力总评`,
      `- **当前职阶段位**：${currentRank.title} (${currentRank.enTitle})`,
      `- **技术段位徽章**：${currentRank.badge}`,
      `- **累计实战经验值**：${totalXP} / ${maxTotalXP} XP`,
      `- **通关关卡数**：${completedCount} / ${totalCount} 阶段 (达成率 ${progressPercent}%)`,
      `- **下一步成长突破**：${currentRank.nextLevelHint}`,
      ``,
      `---`,
      ``,
      `## 二、 六大核心工程技术维度评分`,
      ...domainStats.map(d => `- **${d.name}**：${d.score} / 100 分 (通关 ${d.countDone}/${d.countTotal} 关) —— ${d.description}`),
      ``,
      `---`,
      ``,
      `## 三、 AI 伴学导师全方位诊断评语`,
      `> "${mentorFeedback}"`,
      ``,
      `---`,
      ``,
      `## 四、 已通关荣誉关卡清单`,
      ...phases.filter(p => isPhasePassed(p.id)).map((p, idx) => {
        const meta = typeof completedPhases[p.id] === 'object' ? completedPhases[p.id] : null;
        const dateStr = meta?.passedAt ? new Date(meta.passedAt).toLocaleDateString() : '已通关';
        return `${idx + 1}. [✔] **${p.title}** (${p.difficulty}) | 斩获 +${meta?.xpEarned || getPhaseBaseXP(p)} XP | 达成时间：${dateStr}`;
      }),
      completedCount === 0 ? `- 暂无通关记录，赶快开启第一关吧！` : ``,
      ``,
      `---`,
      `*本报告基于 AgentForge · 智炼工坊 自动化沙箱代码评测真实断言与执行记录生成，具备技术能力认证效力。*`
    ].filter(Boolean).join('\n');
  };

  const handleCopyReport = () => {
    navigator.clipboard.writeText(generateReportMarkdown());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    const text = generateReportMarkdown();
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `AI_Learning_Student_Report_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
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
        padding: '24px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '720px',
          maxHeight: '88vh',
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-border-active)',
          borderRadius: '12px',
          boxShadow: '0 24px 70px rgba(0,0,0,0.6)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.2s ease'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 顶部 Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--wb-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--wb-bg-header)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(34, 197, 94, 0.2))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(59, 130, 246, 0.3)'
            }}>
              <Trophy size={18} color="var(--wb-accent-subtle)" />
            </div>
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--wb-text-bright)', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>AgentForge · 智炼工坊</span>
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--wb-text-sub)' }}>| 技术能力评估报告</span>
              </h3>
              <p style={{ fontSize: '11px', color: 'var(--wb-text-dim)', margin: '2px 0 0 0' }}>
                基于自动化单元评测沙箱与企业级实战记录生成 · 具备认证效力
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={handleCopyReport}
              className="wb-btn-ghost"
              style={{ fontSize: '11.5px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="复制报告 Markdown 格式"
            >
              {copied ? <Check size={12} color="var(--wb-accent-success)" /> : <Copy size={12} />}
              <span>{copied ? '已复制' : '复制报告'}</span>
            </button>

            <button
              onClick={handleDownloadReport}
              className="wb-btn-ghost"
              style={{ fontSize: '11.5px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="下载 Markdown 文件"
            >
              <Download size={12} />
              <span>下载 .md</span>
            </button>

            <button
              onClick={() => window.print()}
              className="wb-btn-ghost"
              style={{ fontSize: '11.5px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="打印报告或另存为 PDF"
            >
              <Printer size={12} />
              <span>打印 PDF</span>
            </button>

            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--wb-text-dim)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex'
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* 报告正文滚动区域 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }} className="wb-custom-scroll">
          
          {/* 1. 学员段位名牌卡片 */}
          <div style={{
            background: 'linear-gradient(135deg, var(--wb-bg-subtle), var(--wb-bg-panel))',
            border: '1px solid var(--wb-border-subtle)',
            borderRadius: '10px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '16px',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: 'rgba(59, 130, 246, 0.15)',
                  color: 'var(--wb-accent-subtle)',
                  border: '1px solid rgba(59, 130, 246, 0.3)'
                }}>
                  {currentRank.badge}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>
                  Level {currentRank.level} / 6
                </span>
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--wb-text-bright)', margin: '4px 0' }}>
                {currentRank.title}
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--wb-text-dim)', margin: 0 }}>
                下一步进阶突破：{currentRank.nextLevelHint}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>实战累计战力</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--wb-accent-amber)' }}>
                  {totalXP} <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--wb-text-dim)' }}>/ {maxTotalXP} XP</span>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: 'var(--wb-text-dim)' }}>通关达成率</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--wb-accent-success)' }}>
                  {progressPercent}% <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--wb-text-dim)' }}>({completedCount}/{totalCount})</span>
                </div>
              </div>
            </div>
          </div>

          {/* 2. 六维能力雷达评分与蛛网几何图 */}
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright)', marginBottom: '10px' }}>
              📊 核心工程能力六维雷达模型
            </h4>

            {/* SVG 极客雷达蛛网图 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'var(--wb-bg-subtle)',
              border: '1px solid var(--wb-border-subtle)',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '12px'
            }}>
              <svg width="280" height="250" viewBox="0 0 280 250" style={{ overflow: 'visible' }}>
                <defs>
                  <linearGradient id="radarFill" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="rgba(59, 130, 246, 0.45)" />
                    <stop offset="100%" stopColor="rgba(34, 197, 94, 0.35)" />
                  </linearGradient>
                </defs>
                {/* 绘制 4 层背景蛛网环 */}
                {[0.25, 0.5, 0.75, 1.0].map((scale, sIdx) => {
                  const r = 90 * scale;
                  const pts = domainStats.map((_, i) => {
                    const angle = (Math.PI * 2 / 6) * i - Math.PI / 2;
                    return `${140 + r * Math.cos(angle)},${125 + r * Math.sin(angle)}`;
                  }).join(' ');
                  return (
                    <polygon
                      key={sIdx}
                      points={pts}
                      fill="none"
                      stroke="var(--wb-border-subtle)"
                      strokeWidth="1"
                      strokeDasharray={scale < 1 ? "2,2" : "none"}
                    />
                  );
                })}

                {/* 6 条轴线与外圈标签 */}
                {domainStats.map((dim, i) => {
                  const angle = (Math.PI * 2 / 6) * i - Math.PI / 2;
                  const x2 = 140 + 90 * Math.cos(angle);
                  const y2 = 125 + 90 * Math.sin(angle);
                  const labelX = 140 + 115 * Math.cos(angle);
                  const labelY = 125 + 112 * Math.sin(angle);
                  return (
                    <g key={i}>
                      <line x1="140" y1="125" x2={x2} y2={y2} stroke="var(--wb-border-subtle)" strokeWidth="1" />
                      <text
                        x={labelX}
                        y={labelY}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fontSize="9.5"
                        fill={dim.score > 0 ? "var(--wb-text-bright)" : "var(--wb-text-dim)"}
                        fontWeight={dim.score > 0 ? "600" : "400"}
                      >
                        {dim.name.split(' ')[0]} ({dim.score})
                      </text>
                    </g>
                  );
                })}

                {/* 实战得分多边形 (动态坐标计算) */}
                {(() => {
                  const polygonPoints = domainStats.map((dim, i) => {
                    const angle = (Math.PI * 2 / 6) * i - Math.PI / 2;
                    // 即使得分为 0，也给一个微小的基准点让雷达具备基本多边形轮廓
                    const r = Math.max(10, 90 * (dim.score / 100));
                    return `${140 + r * Math.cos(angle)},${125 + r * Math.sin(angle)}`;
                  }).join(' ');

                  return (
                    <>
                      <polygon
                        points={polygonPoints}
                        fill="url(#radarFill)"
                        stroke="#38bdf8"
                        strokeWidth="2"
                        strokeLinejoin="round"
                      />
                      {domainStats.map((dim, i) => {
                        const angle = (Math.PI * 2 / 6) * i - Math.PI / 2;
                        const r = Math.max(10, 90 * (dim.score / 100));
                        return (
                          <circle
                            key={i}
                            cx={140 + r * Math.cos(angle)}
                            cy={125 + r * Math.sin(angle)}
                            r={dim.score > 0 ? "3.5" : "2"}
                            fill={dim.score > 0 ? "#38bdf8" : "var(--wb-text-dim)"}
                            stroke="#0f172a"
                            strokeWidth="1.5"
                          />
                        );
                      })}
                    </>
                  );
                })()}
              </svg>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))',
              gap: '10px'
            }}>
              {domainStats.map(dim => {
                const Icon = dim.icon;
                return (
                  <div
                    key={dim.id}
                    style={{
                      background: 'var(--wb-bg-subtle)',
                      border: '1px solid var(--wb-border-subtle)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Icon size={14} color="var(--wb-accent-subtle)" />
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                          {dim.name}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: dim.score > 0 ? 'var(--wb-text-bright)' : 'var(--wb-text-dim)' }}>
                        {dim.score} 分
                      </span>
                    </div>

                    <div style={{
                      width: '100%',
                      height: '4px',
                      background: 'var(--wb-border-subtle)',
                      borderRadius: '2px',
                      overflow: 'hidden',
                      marginBottom: '6px'
                    }}>
                      <div style={{
                        width: `${dim.score}%`,
                        height: '100%',
                        background: dim.score >= 80 ? 'var(--wb-accent-success)' : dim.score > 0 ? 'var(--wb-accent-subtle)' : 'transparent',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--wb-text-dim)' }}>
                      <span>完成进度: {dim.countDone} / {dim.countTotal} 关</span>
                      <span>权重: 工业级核心</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 3. AI 伴学导师全景诊断评语 */}
          <div style={{
            background: 'var(--wb-bg-root)',
            border: '1px solid var(--wb-border-subtle)',
            borderRadius: '10px',
            padding: '14px 16px',
            marginBottom: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Sparkles size={14} style={{ color: 'var(--wb-accent-amber)' }} />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                AI 伴学导师专属能力诊断
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--wb-text-sub)', lineHeight: '1.6', margin: 0 }}>
              {mentorFeedback}
            </p>
          </div>

          {/* 4. 已达成实战战报清单 */}
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright)', marginBottom: '8px' }}>
              🏆 已通关实战荣誉清单 ({completedCount})
            </h4>

            {completedCount === 0 ? (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                background: 'var(--wb-bg-subtle)',
                borderRadius: '8px',
                border: '1px dashed var(--wb-border-subtle)',
                color: 'var(--wb-text-dim)',
                fontSize: '12px'
              }}>
                尚未产生通关实战记录，请在左侧路线开始你的首个关卡挑战！
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))',
                gap: '8px'
              }}>
                {phases.filter(p => isPhasePassed(p.id)).map(p => {
                  const meta = typeof completedPhases[p.id] === 'object' ? completedPhases[p.id] : null;
                  return (
                    <div
                      key={p.id}
                      style={{
                        background: 'var(--wb-bg-subtle)',
                        border: '1px solid rgba(34, 197, 94, 0.2)',
                        borderRadius: '6px',
                        padding: '8px 10px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                        <CheckCircle2 size={12} color="var(--wb-accent-success)" style={{ flexShrink: 0 }} />
                        <span style={{
                          fontSize: '11.5px',
                          color: 'var(--wb-text-bright)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {p.title}
                        </span>
                      </div>
                      <span style={{ fontSize: '10.5px', color: 'var(--wb-accent-success)', fontWeight: 600, flexShrink: 0 }}>
                        +{meta?.xpEarned || getPhaseBaseXP(p)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
