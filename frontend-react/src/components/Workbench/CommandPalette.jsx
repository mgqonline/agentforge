import React, { useState, useEffect, useRef } from 'react';
import { Search, Hash, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function CommandPalette({
  isOpen = false,
  onClose = () => {},
  phases = [],
  completedPhases = {},
  onSelectPhase = () => {}
}) {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = phases.filter(p => 
    p.title.toLowerCase().includes(query.toLowerCase()) ||
    p.id.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="wb-palette-overlay" onClick={onClose}>
      <div className="wb-palette-dialog" onClick={(e) => e.stopPropagation()}>
        {/* 输入框 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '12px 16px',
          borderBottom: '1px solid #222'
        }}>
          <Search size={16} color="#71717a" />
          <input
            ref={inputRef}
            type="text"
            placeholder="跳转到关卡 (例如: 04-rag, Agent, Prompt)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#ededed',
              fontSize: '14px'
            }}
          />
          <kbd style={{
            fontSize: '11px',
            background: '#222',
            padding: '2px 5px',
            borderRadius: '4px',
            color: '#71717a'
          }}>ESC</kbd>
        </div>

        {/* 结果列表 */}
        <div style={{ maxHeight: '320px', overflowY: 'auto', padding: '6px' }} className="wb-custom-scroll">
          {filtered.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#555', fontSize: '13px' }}>
              未匹配到关卡
            </div>
          ) : (
            filtered.map((phase) => {
              const isDone = Boolean(completedPhases[phase.id]);
              return (
                <div
                  key={phase.id}
                  onClick={() => {
                    onSelectPhase(phase.id);
                    onClose();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '13px',
                    color: '#d4d4d8',
                    transition: 'background 0.12s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#1a1a1a'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--wb-font-mono)', color: '#71717a' }}>
                      {String(phase.order).padStart(2, '0')}
                    </span>
                    <span style={{ color: 'var(--wb-text-bright)' }}>
                      {phase.title.replace(/^\d+[-_][a-zA-Z0-9\-_]+\s*[·:：\-—]\s*/, '').replace(/^\d+([-_][a-zA-Z0-9]+)?[\.、\-\s]+\s*/, '')}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {isDone && <CheckCircle2 size={14} color="#22c55e" />}
                    <ArrowRight size={13} color="#555" />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
