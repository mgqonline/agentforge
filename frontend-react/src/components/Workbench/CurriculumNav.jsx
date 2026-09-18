import React, { useState } from 'react';
import { CheckCircle2, Circle, Search, ChevronLeft, Lock, Unlock, Sparkles } from 'lucide-react';

const formatPhaseTitle = (title) => {
  if (!title) return '';
  return title
    .replace(/^\d+[-_][a-zA-Z0-9\-_]+\s*[·:：\-—]\s*/, '')
    .replace(/^\d+([-_][a-zA-Z0-9]+)?[\.、\-\s]+\s*/, '')
    .trim();
};

export default function CurriculumNav({
  phases = [],
  activePhaseId = '',
  completedPhases = {},
  isChallengeMode = true,
  isCollapsed = false,
  isPhaseUnlocked = () => true,
  onToggleCollapse = () => {},
  onToggleChallengeMode = () => {},
  onSelectPhase = () => {}
}) {
  const [filterText, setFilterText] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('ALL'); // ALL, Beginner, Intermediate, Advanced

  const filteredPhases = phases.filter(p => {
    const matchesText = p.title.toLowerCase().includes(filterText.toLowerCase()) || 
                       p.id.toLowerCase().includes(filterText.toLowerCase());
    const matchesDiff = selectedDifficulty === 'ALL' || p.difficulty === selectedDifficulty;
    return matchesText && matchesDiff;
  });

  const handleItemClick = (phase) => {
    onSelectPhase(phase.id);
  };

  return (
    <aside className={`wb-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* 顶部极简搜索与折叠 */}
      <div style={{
        padding: '10px 12px',
        borderBottom: '1px solid var(--wb-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid var(--wb-border-subtle)',
          borderRadius: '5px',
          padding: '4px 8px',
          flex: 1
        }}>
          <Search size={13} color="#71717a" />
          <input
            type="text"
            placeholder="过滤关卡..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#ededed',
              fontSize: '11.5px',
              width: '100%'
            }}
          />
        </div>

        <button
          onClick={onToggleCollapse}
          className="wb-btn-ghost"
          style={{ padding: '4px' }}
          title="收起侧栏 (释放空间)"
        >
          <ChevronLeft size={14} />
        </button>
      </div>

      {/* 学习模式切换胶囊栏 */}
      <div style={{
        padding: '6px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--wb-border-subtle)',
        fontSize: '11px',
        background: 'var(--wb-bg-header)'
      }}>
        <span style={{ color: 'var(--wb-text-dim)' }}>学习模式:</span>
        <button
          onClick={onToggleChallengeMode}
          className="wb-btn-ghost"
          style={{
            fontSize: '10.5px',
            padding: '2px 8px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            color: isChallengeMode ? 'var(--wb-accent-amber)' : 'var(--wb-accent-subtle)',
            borderColor: isChallengeMode ? 'rgba(234, 179, 8, 0.35)' : 'rgba(59, 130, 246, 0.35)',
            background: 'var(--wb-bg-hover)'
          }}
          title={isChallengeMode ? "当前为【闯关进阶模式】：需依序完成前置依赖关卡" : "当前为【自由探索模式】：所有关卡全量免锁开放"}
        >
          {isChallengeMode ? <Lock size={10} /> : <Unlock size={10} />}
          <span>{isChallengeMode ? '闯关进阶' : '自由探索'}</span>
        </button>
      </div>

      {/* 阶梯进阶分级筛选胶囊 (初/中/高) */}
      <div style={{
        padding: '6px 8px',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '4px',
        borderBottom: '1px solid var(--wb-border-subtle)',
        background: 'rgba(0, 0, 0, 0.12)'
      }}>
        {[
          { key: 'ALL', label: '全部' },
          { key: 'Beginner', label: '🟢初级' },
          { key: 'Intermediate', label: '🟡中级' },
          { key: 'Advanced', label: '🔴高级' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setSelectedDifficulty(tab.key)}
            style={{
              padding: '3px 0',
              fontSize: '10px',
              fontWeight: selectedDifficulty === tab.key ? 600 : 400,
              border: `1px solid ${selectedDifficulty === tab.key ? 'var(--wb-accent-primary)' : 'transparent'}`,
              background: selectedDifficulty === tab.key ? 'rgba(59, 130, 246, 0.18)' : 'transparent',
              color: selectedDifficulty === tab.key ? 'var(--wb-text-bright)' : 'var(--wb-text-dim)',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 极简列表条目 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 8px' }} className="wb-custom-scroll">
        <div style={{
          fontSize: '11px',
          color: '#52525b',
          fontWeight: 600,
          textTransform: 'uppercase',
          padding: '4px 6px',
          display: 'flex',
          justifyContent: 'space-between',
          letterSpacing: '0.04em'
        }}>
          <span>实战路线 ({filteredPhases.length})</span>
          {selectedDifficulty !== 'ALL' && (
            <span style={{ fontSize: '10px', color: 'var(--wb-accent-primary)' }}>
              {selectedDifficulty}
            </span>
          )}
        </div>

        {filteredPhases.map((phase) => {
          const isActive = phase.id === activePhaseId;
          const isDone = Boolean(completedPhases[phase.id]?.passed || completedPhases[phase.id]);
          const isUnlocked = isPhaseUnlocked(phase.id);
          const cleanTitle = formatPhaseTitle(phase.title);

          const diffColor = phase.difficulty === 'Beginner'
            ? '#22c55e'
            : phase.difficulty === 'Intermediate'
              ? '#eab308'
              : '#ef4444';
          const diffShort = phase.difficulty === 'Beginner' ? '初' : phase.difficulty === 'Intermediate' ? '中' : '高';

          return (
            <div
              key={phase.id}
              onClick={() => handleItemClick(phase)}
              className={`wb-phase-item ${isActive ? 'active' : ''}`}
              style={{
                opacity: (!isUnlocked && isChallengeMode) ? 0.62 : 1,
                cursor: 'pointer'
              }}
              title={!isUnlocked && isChallengeMode ? `${cleanTitle}（前置未完成，可自由查阅演练）` : cleanTitle}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                <span style={{
                  fontSize: '11px',
                  fontFamily: 'var(--wb-font-mono)',
                  color: isActive ? 'var(--wb-accent-primary)' : '#71717a',
                  width: '18px',
                  flexShrink: 0
                }}>
                  {String(phase.order).padStart(2, '0')}
                </span>

                <span style={{
                  fontSize: '9px',
                  lineHeight: '13px',
                  padding: '1px 3px',
                  borderRadius: '3px',
                  color: diffColor,
                  border: `1px solid ${diffColor}44`,
                  background: `${diffColor}15`,
                  flexShrink: 0,
                  fontWeight: 600
                }}>
                  {diffShort}
                </span>

                <span style={{
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  fontSize: '12px',
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? 'var(--wb-text-bright)' : (!isUnlocked && isChallengeMode) ? 'var(--wb-text-dim)' : undefined
                }}>
                  {cleanTitle}
                </span>
              </div>

              <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', marginLeft: '6px' }}>
                {isDone ? (
                  <CheckCircle2 size={13} color="#22c55e" />
                ) : !isUnlocked && isChallengeMode ? (
                  <Lock size={12} color="var(--wb-text-dim)" />
                ) : (
                  <Circle size={10} color={isActive ? '#52525b' : '#27272a'} />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
