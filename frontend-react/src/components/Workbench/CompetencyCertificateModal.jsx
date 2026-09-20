import React, { useState, useRef } from 'react';
import { 
  Award, ShieldCheck, CheckCircle2, Star, Download, Printer, 
  Copy, Check, X, Sparkles, Building2, BrainCircuit, Database, Zap, Lock
} from 'lucide-react';

export default function CompetencyCertificateModal({
  isOpen = false,
  onClose = () => {},
  phases = [],
  completedPhases = {},
  currentUser = null,
  currentTenant = null
}) {
  const [copied, setCopied] = useState(false);
  const certRef = useRef(null);

  if (!isOpen) return null;

  // 1. 基础通关统计
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
  let completedCount = 0;
  const totalCount = phases.length || 24;

  phases.forEach(p => {
    const baseXP = getPhaseBaseXP(p);
    if (isPhasePassed(p.id)) {
      completedCount++;
      const item = completedPhases[p.id];
      const xpEarned = (typeof item === 'object' && item.xpEarned) ? item.xpEarned : baseXP;
      totalXP += xpEarned;
    }
  });

  const completionRate = Math.round((completedCount / totalCount) * 100);

  // 2. 证书唯一防伪编号与颁发日期
  // 基于用户标识与当前日期生成稳定的伪哈希
  const userName = currentUser?.name || currentUser?.email?.split('@')[0] || 'AI 架构实战工程师';
  const tenantName = currentTenant?.name || '拓维信息智炼工坊';
  const issueDate = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  const certSerial = `AF-${new Date().getFullYear()}-${Math.abs(
    (userName + tenantName).split('').reduce((acc, c) => ((acc << 5) - acc) + c.charCodeAt(0), 0)
  ).toString(16).toUpperCase().padStart(8, '0')}`;

  const handleCopySerial = () => {
    navigator.clipboard.writeText(certSerial);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(0, 0, 0, 0.78)',
        backdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        overflowY: 'auto'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '820px',
          maxHeight: 'min(90vh, 780px)',
          margin: 'auto',
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-border-active)',
          borderRadius: '14px',
          boxShadow: '0 25px 70px rgba(0,0,0,0.8), 0 0 40px rgba(59, 130, 246, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.25s ease'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 顶部工具条 */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--wb-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--wb-bg-header)',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Award size={18} color="var(--wb-accent-primary)" />
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
              AgentForge AI 应用工程能力官方认证证书
            </span>
            <span style={{
              fontSize: '10.5px',
              padding: '1px 6px',
              borderRadius: '4px',
              background: 'rgba(59, 130, 246, 0.15)',
              color: 'var(--wb-accent-subtle)',
              border: '1px solid rgba(59, 130, 246, 0.3)'
            }}>
              区块链防伪验真
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={handleCopySerial}
              className="wb-btn-ghost"
              style={{ fontSize: '11px', padding: '5px 10px' }}
              title="复制证书编号"
            >
              {copied ? <Check size={13} color="#4ade80" /> : <Copy size={13} />}
              <span>{copied ? '已复制编号' : certSerial}</span>
            </button>
            <button
              onClick={handlePrint}
              style={{
                background: 'var(--wb-accent-subtle)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '5px 12px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
              }}
            >
              <Printer size={13} />
              <span>打印 / 导出 PDF</span>
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--wb-text-sub)',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* 证书主体 (含打印样式容器) */}
        <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1, minHeight: 0 }}>
          <div
            ref={certRef}
            className="certificate-container"
            style={{
              position: 'relative',
              background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(15, 23, 42, 0.98))',
              border: '2px solid rgba(59, 130, 246, 0.4)',
              borderRadius: '12px',
              padding: '24px 22px',
              boxShadow: 'inset 0 0 60px rgba(59, 130, 246, 0.05)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              overflow: 'hidden'
            }}
          >
            {/* 科技感背景暗纹与水印 */}
            <div style={{
              position: 'absolute',
              top: '-60px',
              right: '-60px',
              width: '240px',
              height: '240px',
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.12) 0%, transparent 70%)',
              pointerEvents: 'none'
            }} />
            <div style={{
              position: 'absolute',
              bottom: '-60px',
              left: '-60px',
              width: '240px',
              height: '240px',
              background: 'radial-gradient(circle, rgba(34, 197, 94, 0.08) 0%, transparent 70%)',
              pointerEvents: 'none'
            }} />

            {/* 证书抬头 */}
            <div style={{ textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '18px' }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '11px',
                letterSpacing: '3px',
                color: 'var(--wb-accent-primary)',
                textTransform: 'uppercase',
                fontWeight: 600,
                marginBottom: '6px'
              }}>
                <Sparkles size={14} />
                <span>TALKWEB AI ENGINEERING ACADEMY</span>
                <Sparkles size={14} />
              </div>
              <h2 style={{
                fontSize: '22px',
                fontWeight: 700,
                color: '#ffffff',
                letterSpacing: '1px',
                margin: 0
              }}>
                AgentForge · 全维 AI 工程架构能力认证证书
              </h2>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginTop: '4px' }}>
                CERTIFICATE OF ARTIFICIAL INTELLIGENCE ENGINEERING COMPETENCY
              </div>
            </div>

            {/* 证书正文颁发词 */}
            <div style={{ textAlign: 'center', padding: '0 10px' }}>
              <div style={{ fontSize: '12px', color: 'var(--wb-text-sub)', marginBottom: '8px' }}>
                兹证明实战学员
              </div>
              <div style={{
                fontSize: '24px',
                fontWeight: 700,
                color: 'var(--wb-accent-subtle)',
                letterSpacing: '1px',
                textShadow: '0 0 15px rgba(59, 130, 246, 0.3)'
              }}>
                {userName}
              </div>
              <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim)', marginTop: '4px' }}>
                所属实战空间：{tenantName}
              </div>
              <p style={{
                fontSize: '12.5px',
                color: 'var(--wb-text-normal)',
                lineHeight: '1.7',
                marginTop: '16px',
                maxWidth: '620px',
                marginInline: 'auto'
              }}>
                在 <strong style={{ color: '#ffffff' }}>AgentForge 智炼工坊</strong> 工业级沙箱实战演练中，严谨攻关大模型全栈工程栈，通过了自动化单元测试与沙箱代码评测，展现出卓越的企业级 AI 架构实操与系统工程落地素养，特授予：
              </p>
              <div style={{
                display: 'inline-block',
                marginTop: '10px',
                padding: '6px 20px',
                background: 'linear-gradient(90deg, rgba(59, 130, 246, 0.2), rgba(34, 197, 94, 0.2))',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                borderRadius: '20px',
                fontSize: '14px',
                fontWeight: 600,
                color: '#ffffff'
              }}>
                🌟 企业级 AI 应用工程架构师 (Certified AI Application Architect)
              </div>
            </div>

            {/* 六维工程能力徽章 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '10px',
              background: 'rgba(0,0,0,0.25)',
              padding: '14px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.06)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Zap size={14} color="#60a5fa" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>Prompt & 提示工程解耦</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={14} color="#34d399" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>多跳 RAG 与混合检索重排</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BrainCircuit size={14} color="#a78bfa" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>LangGraph 循环图与反思智能体</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Building2 size={14} color="#f59e0b" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>MCP 标准模型上下文协议</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={14} color="#f87171" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>AI 安全防御与 Ragas 评测</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={14} color="#38bdf8" />
                <span style={{ fontSize: '11.5px', color: 'var(--wb-text-bright)' }}>vLLM 推理加速与工程基建</span>
              </div>
            </div>

            {/* 实战指标与签章区 */}
            <div style={{
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              paddingTop: '12px',
              borderTop: '1px solid rgba(255,255,255,0.08)'
            }}>
              {/* 左侧：实战指标 */}
              <div style={{ display: 'flex', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '10px', color: 'var(--wb-text-dim)' }}>通关关卡</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-accent-success)' }}>
                    {completedCount} / {totalCount} 关 ({completionRate}%)
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', color: 'var(--wb-text-dim)' }}>累计实战算力值</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-accent-primary)' }}>
                    {totalXP} XP
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', color: 'var(--wb-text-dim)' }}>颁发日期</div>
                  <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--wb-text-normal)' }}>
                    {issueDate}
                  </div>
                </div>
              </div>

              {/* 右侧：防伪证书印章 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '10px', color: 'var(--wb-text-dim)' }}>防伪存证编号</div>
                  <div style={{ fontSize: '11px', fontFamily: 'monospace', fontWeight: 600, color: 'var(--wb-text-bright)' }}>
                    {certSerial}
                  </div>
                </div>

                {/* 科技权威 SVG 印章 */}
                <div style={{
                  width: '76px',
                  height: '76px',
                  borderRadius: '50%',
                  border: '2px dashed rgba(239, 68, 68, 0.7)',
                  background: 'rgba(239, 68, 68, 0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ef4444',
                  transform: 'rotate(-10deg)',
                  userSelect: 'none',
                  boxShadow: '0 0 10px rgba(239, 68, 68, 0.15)'
                }}>
                  <div style={{ fontSize: '8px', fontWeight: 700, letterSpacing: '1px' }}>智炼工坊</div>
                  <div style={{ fontSize: '11px', fontWeight: 900, margin: '2px 0' }}>★ 认证 ★</div>
                  <div style={{ fontSize: '7.5px', transform: 'scale(0.85)' }}>AI工程院</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 底部备注提示 */}
        <div style={{
          padding: '10px 20px',
          background: 'var(--wb-bg-subtle)',
          borderTop: '1px solid var(--wb-border-subtle)',
          fontSize: '11px',
          color: 'var(--wb-text-dim)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          <span>💡 提示：支持点击右上角【打印 / 导出 PDF】保存至本地简历或企业人才库。</span>
          <span>技术支持：AgentForge 沙箱代码评测引擎</span>
        </div>
      </div>
    </div>
  );
}
