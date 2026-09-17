import React, { useState, useRef, useEffect } from 'react';
import { Palette, Check } from 'lucide-react';

export const THEMES = [
  {
    id: 'obsidian',
    name: '曜石极客黑',
    desc: '极简深黑，沉浸专注 (默认)',
    bg: '#050505',
    accent: '#3b82f6',
    border: '#222222',
    isLight: false
  },
  {
    id: 'nordic',
    name: '北欧石板灰蓝',
    desc: '深海岩灰，低反差舒缓眼疲劳',
    bg: '#0b0f19',
    accent: '#38bdf8',
    border: '#1e293b',
    isLight: false
  },
  {
    id: 'sepia',
    name: '墨玉护眼竹韵',
    desc: '草木墨青，长时间阅读防干眼',
    bg: '#091210',
    accent: '#10b981',
    border: '#1c322c',
    isLight: false
  },
  {
    id: 'paper',
    name: '现代纸墨雅白',
    desc: '纯净高亮，适合强光与日间办公',
    bg: '#f8fafc',
    accent: '#2563eb',
    border: '#e2e8f0',
    isLight: true
  }
];

export default function ThemeSwitcher({ currentTheme = 'obsidian', onSelectTheme = () => {} }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeThemeObj = THEMES.find(t => t.id === currentTheme) || THEMES[0];

  return (
    <div style={{ position: 'relative' }} ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="wb-btn-ghost"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 8px',
          borderRadius: '5px',
          border: '1px solid var(--wb-border-subtle)'
        }}
        title="切换界面调色主题 (满足不同光线与人群护眼需求)"
      >
        <div style={{
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          background: activeThemeObj.bg,
          border: `1.5px solid ${activeThemeObj.accent}`
        }} />
        <span style={{ fontSize: '11.5px' }}>{activeThemeObj.name}</span>
        <Palette size={11} color="var(--wb-text-dim)" />
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          width: '240px',
          background: 'var(--wb-bg-panel)',
          border: '1px solid var(--wb-border-subtle)',
          borderRadius: '8px',
          boxShadow: '0 12px 32px rgba(0, 0, 0, 0.3)',
          padding: '6px',
          zIndex: 100
        }}>
          <div style={{
            fontSize: '10.5px',
            color: 'var(--wb-text-dim)',
            padding: '4px 8px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em'
          }}>
            界面配色与人群偏好
          </div>

          {THEMES.map((theme) => {
            const isSelected = theme.id === currentTheme;
            return (
              <div
                key={theme.id}
                onClick={() => {
                  onSelectTheme(theme.id);
                  setIsOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '7px 8px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  background: isSelected ? 'var(--wb-bg-subtle)' : 'transparent',
                  color: isSelected ? 'var(--wb-text-bright)' : 'var(--wb-text-sub)',
                  fontSize: '12px',
                  transition: 'background 0.12s'
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'var(--wb-bg-hover)';
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'transparent';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {/* 色彩预览小圆环 */}
                  <div style={{
                    width: '14px',
                    height: '14px',
                    borderRadius: '50%',
                    background: theme.bg,
                    border: `2px solid ${theme.accent}`,
                    flexShrink: 0
                  }} />
                  <div>
                    <div style={{ fontWeight: isSelected ? 600 : 400 }}>{theme.name}</div>
                    <div style={{ fontSize: '10px', color: 'var(--wb-text-dim)', marginTop: '1px' }}>
                      {theme.desc}
                    </div>
                  </div>
                </div>

                {isSelected && <Check size={14} color="var(--wb-accent-subtle)" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
