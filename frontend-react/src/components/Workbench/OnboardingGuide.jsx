/**
 * OnboardingGuide — 新手操作手册
 *
 * 功能：首次进入系统时自动弹出，分步引导用户完成关键操作。
 * 支持：跳过教程、步进导航、重新触发（由 HeaderBar "帮助" 按钮调用）。
 * 存储：localStorage.agentforge_onboarding_done = 'true' 标记已阅读
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, Code2, Play, CheckCircle, ChevronRight, ChevronLeft,
  X, Sparkles, Lightbulb, Target, Rocket, MapPin, SkipForward
} from 'lucide-react';

// ─── 步骤定义 ──────────────────────────────────────────────────────────────────
const STEPS = [
  {
    id: 'welcome',
    icon: <Sparkles size={32} color="#3b82f6" />,
    title: '欢迎来到 AgentForge 智炼工坊 ⚡',
    badge: '第 1 步 · 系统介绍',
    badgeColor: '#3b82f6',
    content: (
      <div>
        <p style={{ marginBottom: '12px', lineHeight: 1.7 }}>
          <strong>智炼工坊</strong>是一个面向 AI 工程师的<strong>交互式实战学习平台</strong>，
          覆盖从 Prompt 工程到生产级多智能体系统的完整知识路线。
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '12px' }}>
          {[
            { icon: '🟢', label: '初级阶段', desc: '6 关 · Prompt/RAG/MCP 基础' },
            { icon: '🟡', label: '中级阶段', desc: '11 关 · FastAPI/Agent/多模态' },
            { icon: '🔴', label: '高级阶段', desc: '9 关 · 推理/微调/RL/图谱' },
            { icon: '🏆', label: '闯关通关', desc: '沙箱验证 · XP 经验值体系' },
          ].map(item => (
            <div key={item.label} style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-start'
            }}>
              <span style={{ fontSize: '18px' }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#e2e8f0', marginBottom: '2px' }}>{item.label}</div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
    tip: '💡 本平台支持深色/浅色主题切换，点击右上角调色板图标即可切换。',
  },
  {
    id: 'select-phase',
    icon: <MapPin size={32} color="#10b981" />,
    title: '选择你的第一个关卡',
    badge: '第 2 步 · 关卡导航',
    badgeColor: '#10b981',
    content: (
      <div>
        <p style={{ marginBottom: '14px', lineHeight: 1.7 }}>
          在屏幕<strong>左侧侧边栏</strong>中，你可以看到所有学习关卡。
          关卡按 <span style={{ color: '#4ade80', fontWeight: 600 }}>初级</span> →{' '}
          <span style={{ color: '#fbbf24', fontWeight: 600 }}>中级</span> →{' '}
          <span style={{ color: '#f87171', fontWeight: 600 }}>高级</span> 顺序排列。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[
            { step: '①', text: '点击顶部筛选胶囊（全部 / 🟢初级 / 🟡中级 / 🔴高级）', color: '#60a5fa' },
            { step: '②', text: '点击列表中的 01 · 提示词工程核心技术 开始初级第一关', color: '#60a5fa' },
            { step: '③', text: '完成一关后，下一关才会解锁（闯关模式）', color: '#60a5fa' },
            { step: '④', text: '也可点击右上角"自由模式"开关跳过前置依赖', color: '#94a3b8' },
          ].map(item => (
            <div key={item.step} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
              <span style={{
                flexShrink: 0,
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: 'rgba(59, 130, 246, 0.2)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '11px',
                fontWeight: 700,
                color: '#60a5fa'
              }}>{item.step}</span>
              <span style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: 1.5, paddingTop: '3px' }}>{item.text}</span>
            </div>
          ))}
        </div>
      </div>
    ),
    tip: '💡 使用 ⌘K（Mac）或 Ctrl+K（Windows）可快速搜索并跳转到任意关卡。',
    highlight: 'sidebar',
  },
  {
    id: 'read-guide',
    icon: <BookOpen size={32} color="#a78bfa" />,
    title: '阅读知识手册',
    badge: '第 3 步 · 知识学习',
    badgeColor: '#a78bfa',
    content: (
      <div>
        <p style={{ marginBottom: '14px', lineHeight: 1.7 }}>
          选择关卡后，<strong>中间面板</strong>是该关卡的<strong>知识手册</strong>，
          包含理论说明、代码示例、架构图和实战提示。
        </p>
        <div style={{
          padding: '12px',
          borderRadius: '8px',
          background: 'rgba(167, 139, 250, 0.08)',
          border: '1px solid rgba(167, 139, 250, 0.2)',
          marginBottom: '12px'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#a78bfa', marginBottom: '8px' }}>📚 手册包含内容：</div>
          {[
            '核心概念与背景知识',
            '完整代码示例（可直接复制）',
            '流程图 / 架构图辅助理解',
            '知识点总结 & 执行命令总结',
            '实战作业题目',
          ].map(item => (
            <div key={item} style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px' }}>
              <CheckCircle size={12} color="#4ade80" />
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{item}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
          手册支持<strong>折叠/展开</strong>（点击顶部 Panel 图标），
          建议先完整阅读一遍再动手写代码。
        </p>
      </div>
    ),
    tip: '💡 手册内的代码片段可以点击复制到右侧编辑器，减少手动输入。',
    highlight: 'guide',
  },
  {
    id: 'write-code',
    icon: <Code2 size={32} color="#f59e0b" />,
    title: '在代码编辑器中编写代码',
    badge: '第 4 步 · 动手实战',
    badgeColor: '#f59e0b',
    content: (
      <div>
        <p style={{ marginBottom: '14px', lineHeight: 1.7 }}>
          右侧是 <strong>Monaco 代码编辑器</strong>（VS Code 同款内核），
          已预加载该关卡的<strong>骨架代码（Starter Code）</strong>，
          你需要填充核心逻辑。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[
            { label: '骨架代码', desc: '包含函数签名和 TODO 注释，引导你填写关键实现', color: '#fbbf24' },
            { label: '解题参考', desc: '点击"查看答案"按钮可查看标准实现作为参考', color: '#60a5fa' },
            { label: '多文件支持', desc: '关卡包含多个脚本时，顶部文件栏可切换查看', color: '#4ade80' },
            { label: '快捷键支持', desc: 'Ctrl+S 保存、⌘+Enter 运行、Tab 补全', color: '#a78bfa' },
          ].map(item => (
            <div key={item.label} style={{
              padding: '8px 12px',
              borderRadius: '6px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-start'
            }}>
              <div style={{
                flexShrink: 0,
                fontSize: '11px',
                fontWeight: 700,
                color: item.color,
                paddingTop: '1px',
                minWidth: '60px'
              }}>{item.label}</div>
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    ),
    tip: '💡 编辑器支持 Python 语法高亮、错误提示与自动补全，与 VS Code 快捷键完全兼容。',
    highlight: 'editor',
  },
  {
    id: 'run-sandbox',
    icon: <Play size={32} color="#22c55e" />,
    title: '运行沙箱验证代码',
    badge: '第 5 步 · 沙箱执行',
    badgeColor: '#22c55e',
    content: (
      <div>
        <p style={{ marginBottom: '14px', lineHeight: 1.7 }}>
          代码写好后，点击 <strong>「▶ 运行代码」</strong> 按钮（或按 <kbd style={{
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '4px',
            padding: '1px 6px',
            fontSize: '12px'
          }}>⌘ + Enter</kbd>）执行沙箱验证。
        </p>
        <div style={{
          padding: '12px',
          borderRadius: '8px',
          background: 'rgba(34, 197, 94, 0.06)',
          border: '1px solid rgba(34, 197, 94, 0.2)',
          marginBottom: '12px'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#4ade80', marginBottom: '8px' }}>🛡️ 沙箱安全特性：</div>
          {[
            '代码在完全隔离的 Docker 沙箱中执行，不影响宿主环境',
            '每次执行有 30 秒超时保护，防止死循环卡死',
            '自动屏蔽危险系统调用，保障平台与用户安全',
            '执行结果实时流式输出到底部控制台面板',
          ].map(item => (
            <div key={item} style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', marginBottom: '4px' }}>
              <CheckCircle size={11} color="#4ade80" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{item}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
          控制台会显示<strong>标准输出</strong>、<strong>错误信息</strong>和<strong>执行时长</strong>，
          帮助你定位代码问题。
        </p>
      </div>
    ),
    tip: '💡 右上角的绿点 = 沙箱在线，红点 = 沙箱离线（此时可查看知识手册但无法执行代码）。',
  },
  {
    id: 'pass-phase',
    icon: <Target size={32} color="#f43f5e" />,
    title: '验证通关 & 解锁下一关',
    badge: '第 6 步 · 通关验证',
    badgeColor: '#f43f5e',
    content: (
      <div>
        <p style={{ marginBottom: '14px', lineHeight: 1.7 }}>
          运行代码后，点击 <strong>「🏆 验证通关」</strong> 按钮，
          系统会自动运行该关卡的<strong>单元测试套件</strong>，评估你的实现是否正确。
        </p>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          padding: '12px',
          borderRadius: '8px',
          background: 'rgba(244, 63, 94, 0.06)',
          border: '1px solid rgba(244, 63, 94, 0.2)',
          marginBottom: '12px'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#fb7185', marginBottom: '4px' }}>📊 通关判定标准：</div>
          {[
            { label: '全部测试通过', desc: '获得 XP 经验值，关卡点亮为绿色 ✅', color: '#4ade80' },
            { label: '部分测试通过', desc: '继续修改代码再试，可多次提交', color: '#fbbf24' },
            { label: '测试失败', desc: '查看失败原因，参考手册和答案重新实现', color: '#f87171' },
          ].map(item => (
            <div key={item.label} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
              <span style={{ flexShrink: 0, width: '80px', fontSize: '11px', fontWeight: 600, color: item.color, paddingTop: '1px' }}>{item.label}</span>
              <span style={{ fontSize: '12px', color: '#94a3b8' }}>{item.desc}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.6 }}>
          通关后，进度会自动同步到云端，退出后重新登录<strong>进度不丢失</strong>。
        </p>
      </div>
    ),
    tip: '💡 打开顶部"概览"视图可看到你的能力雷达图和各知识领域进度。',
  },
  {
    id: 'finish',
    icon: <Rocket size={32} color="#f59e0b" />,
    title: '你已准备好出发了！🎉',
    badge: '完成 · 开始学习',
    badgeColor: '#f59e0b',
    content: (
      <div>
        <p style={{ marginBottom: '16px', lineHeight: 1.7 }}>
          恭喜完成入门引导！以下是一些有用的<strong>常用功能入口</strong>，
          随时可以通过顶部导航栏访问：
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
          {[
            { icon: '⌘K', label: '快速跳转', desc: '搜索任意关卡' },
            { icon: '📊', label: '概览仪表盘', desc: '查看学习雷达图' },
            { icon: '🏆', label: '能力诊断报告', desc: '生成详细评估' },
            { icon: '📚', label: '企业知识库', desc: 'RAG 文档管理' },
            { icon: '🎨', label: '主题切换', desc: '4 种配色方案' },
            { icon: '❓', label: '帮助 (本手册)', desc: '随时可重新打开' },
          ].map(item => (
            <div key={item.label} style={{
              padding: '10px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              gap: '8px',
              alignItems: 'center'
            }}>
              <span style={{ fontSize: '18px', flexShrink: 0 }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#e2e8f0' }}>{item.label}</div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{
          padding: '10px 14px',
          borderRadius: '8px',
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          fontSize: '12px',
          color: '#93c5fd',
          lineHeight: 1.6
        }}>
          🚀 建议路线：从 <strong>01 · 提示词工程</strong> 开始，按顺序完成初级 6 关后，
          再挑战中级和高级阶段。每关约 30 ~ 60 分钟。
        </div>
      </div>
    ),
    tip: null,
  },
];

// ─── 主组件 ────────────────────────────────────────────────────────────────────
export default function OnboardingGuide({ isOpen, onClose }) {
  const [step, setStep] = useState(0);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  // 每次打开都重置到第一步
  useEffect(() => {
    if (isOpen) setStep(0);
  }, [isOpen]);

  const handleClose = useCallback((markDone = true) => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsAnimatingOut(false);
      if (markDone) {
        try {
          localStorage.setItem('agentforge_onboarding_done', 'true');
        } catch {}
      }
      onClose();
    }, 220);
  }, [onClose]);

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1);
    } else {
      handleClose(true);
    }
  };

  const handlePrev = () => {
    if (step > 0) setStep(s => s - 1);
  };

  if (!isOpen) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;
  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    /* 遮罩层 */
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9000,
        background: 'rgba(0, 0, 0, 0.72)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        animation: isAnimatingOut ? 'onboarding-fade-out 0.22s ease forwards' : 'onboarding-fade-in 0.25s ease',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(false); }}
    >
      <style>{`
        @keyframes onboarding-fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes onboarding-fade-out {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        @keyframes onboarding-slide-in {
          from { opacity: 0; transform: translateY(16px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .ob-card { animation: onboarding-slide-in 0.3s cubic-bezier(.22,.68,0,1.2); }
        .ob-step-dot { transition: all 0.2s ease; }
        .ob-btn { transition: all 0.15s ease; cursor: pointer; }
        .ob-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
        .ob-btn:active { transform: translateY(0); }
      `}</style>

      {/* 主卡片 */}
      <div
        className="ob-card"
        key={step} // key 变化触发重新动画
        style={{
          width: '100%',
          maxWidth: '520px',
          background: '#0f1117',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '16px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 顶部进度条 */}
        <div style={{ height: '3px', background: 'rgba(255,255,255,0.07)', flexShrink: 0 }}>
          <div style={{
            height: '100%',
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
            transition: 'width 0.35s cubic-bezier(.4,0,.2,1)',
            borderRadius: '0 3px 3px 0',
          }} />
        </div>

        {/* 头部：徽章 + 关闭按钮 */}
        <div style={{
          padding: '16px 20px 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 700,
            color: current.badgeColor,
            background: `${current.badgeColor}18`,
            border: `1px solid ${current.badgeColor}30`,
            borderRadius: '20px',
            padding: '3px 10px',
            letterSpacing: '0.3px',
          }}>
            {current.badge}
          </span>
          <button
            className="ob-btn"
            onClick={() => handleClose(false)}
            title="关闭（不标记为已读）"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '6px',
              padding: '4px',
              color: '#64748b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={14} />
          </button>
        </div>

        {/* 正文 */}
        <div style={{ padding: '20px 24px', flex: 1, overflowY: 'auto', maxHeight: '60vh' }}>
          {/* 图标 + 标题 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '18px' }}>
            <div style={{
              flexShrink: 0,
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {current.icon}
            </div>
            <h2 style={{
              fontSize: '17px',
              fontWeight: 800,
              color: '#f1f5f9',
              lineHeight: 1.3,
              letterSpacing: '-0.3px',
            }}>
              {current.title}
            </h2>
          </div>

          {/* 步骤内容 */}
          <div style={{ color: '#94a3b8', fontSize: '13px' }}>
            {current.content}
          </div>

          {/* 小贴士 */}
          {current.tip && (
            <div style={{
              marginTop: '16px',
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(251, 191, 36, 0.06)',
              border: '1px solid rgba(251, 191, 36, 0.2)',
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-start',
            }}>
              <Lightbulb size={14} color="#fbbf24" style={{ flexShrink: 0, marginTop: '1px' }} />
              <span style={{ fontSize: '12px', color: '#fcd34d', lineHeight: 1.6 }}>{current.tip}</span>
            </div>
          )}
        </div>

        {/* 底部导航 */}
        <div style={{
          padding: '14px 24px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          borderTop: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(0,0,0,0.2)',
        }}>
          {/* 步骤点 */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {STEPS.map((_, i) => (
              <button
                key={i}
                className="ob-step-dot"
                onClick={() => setStep(i)}
                style={{
                  width: i === step ? '18px' : '6px',
                  height: '6px',
                  borderRadius: '3px',
                  background: i === step
                    ? current.badgeColor
                    : i < step
                    ? 'rgba(255,255,255,0.3)'
                    : 'rgba(255,255,255,0.12)',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                }}
                aria-label={`跳转到第 ${i + 1} 步`}
              />
            ))}
          </div>

          {/* 操作按钮组 */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {/* 跳过按钮（仅非最后步显示） */}
            {!isLast && (
              <button
                className="ob-btn"
                onClick={() => handleClose(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  borderRadius: '7px',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#64748b',
                  fontSize: '12px',
                }}
              >
                <SkipForward size={12} />
                跳过教程
              </button>
            )}

            {/* 上一步 */}
            {step > 0 && (
              <button
                className="ob-btn"
                onClick={handlePrev}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '7px 14px',
                  borderRadius: '8px',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#94a3b8',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                <ChevronLeft size={14} />
                上一步
              </button>
            )}

            {/* 下一步 / 开始学习 */}
            <button
              className="ob-btn"
              onClick={handleNext}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 18px',
                borderRadius: '8px',
                background: isLast
                  ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                  : `linear-gradient(135deg, ${current.badgeColor}, ${current.badgeColor}bb)`,
                border: 'none',
                color: '#fff',
                fontSize: '13px',
                fontWeight: 700,
                boxShadow: `0 4px 14px ${current.badgeColor}40`,
              }}
            >
              {isLast ? (
                <>
                  <Rocket size={14} />
                  开始学习！
                </>
              ) : (
                <>
                  下一步
                  <ChevronRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
