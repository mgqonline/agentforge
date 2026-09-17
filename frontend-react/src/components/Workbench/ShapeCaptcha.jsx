import React, { useState, useEffect, useCallback } from 'react';
import { RotateCw, CheckCircle2, ShieldAlert, Sparkles } from 'lucide-react';

// 几何图形种类与颜色板
const SHAPE_TYPES = ['circle', 'square', 'triangle', 'star', 'diamond'];
const COLOR_PALETTE = [
  '#38bdf8', // 天蓝
  '#34d399', // 翡翠绿
  '#f472b6', // 樱粉
  '#fbbf24', // 暖黄
  '#a78bfa', // 丁香紫
  '#fb923c', // 珊瑚橙
];

// 四个明确的尺寸阶梯 (16px 为绝对最小)
const SIZE_STEPS = [16, 26, 36, 46];

export default function ShapeCaptcha({ onVerify, isVerified, resetTrigger }) {
  const [shapes, setShapes] = useState([]);
  const [statusMessage, setStatusMessage] = useState('请点击下方【最小】的图形完成验证');
  const [shake, setShake] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(null);

  // 生成一组随机图形（保证最小图形唯一且随机分布）
  const generateCaptcha = useCallback(() => {
    // 随机乱序尺寸梯度 [16, 26, 36, 46]
    const shuffledSizes = [...SIZE_STEPS].sort(() => Math.random() - 0.5);
    
    // 随机挑选 4 个不重复（或尽量丰富）的形状
    const availableShapes = [...SHAPE_TYPES].sort(() => Math.random() - 0.5);
    // 随机颜色
    const availableColors = [...COLOR_PALETTE].sort(() => Math.random() - 0.5);

    const newShapes = shuffledSizes.map((size, idx) => ({
      id: `shape-${idx}-${Date.now()}`,
      type: availableShapes[idx % availableShapes.length],
      size,
      color: availableColors[idx % availableColors.length],
      isSmallest: size === 16,
    }));

    setShapes(newShapes);
    setSelectedIndex(null);
    setStatusMessage('请点击下方【最小】的图形完成验证');
  }, []);

  // 初始化与外部重置监听
  useEffect(() => {
    generateCaptcha();
  }, [generateCaptcha, resetTrigger]);

  // 点击图形事件
  const handleShapeClick = (shape, index) => {
    if (isVerified) return;

    setSelectedIndex(index);

    if (shape.isSmallest) {
      // 验证成功！
      setStatusMessage('验证通过！人机安全检验已确认');
      onVerify(true);
    } else {
      // 选择错误
      setShake(true);
      setStatusMessage('❌ 选择错误，请重新点击最小的图形');
      onVerify(false);
      setTimeout(() => {
        setShake(false);
        generateCaptcha();
      }, 700);
    }
  };

  // 渲染单个 SVG 图形
  const renderShapeSvg = (shape) => {
    const { type, size, color } = shape;
    const cx = 28;
    const cy = 28;

    switch (type) {
      case 'circle':
        return <circle cx={cx} cy={cy} r={size / 2} fill={color} />;
      
      case 'square': {
        const half = size / 2;
        return (
          <rect
            x={cx - half}
            y={cy - half}
            width={size}
            height={size}
            rx={Math.max(2, size / 8)}
            fill={color}
          />
        );
      }

      case 'triangle': {
        // 正三角形
        const h = (size * Math.sqrt(3)) / 2;
        const x1 = cx;
        const y1 = cy - (2 / 3) * h;
        const x2 = cx + size / 2;
        const y2 = cy + (1 / 3) * h;
        const x3 = cx - size / 2;
        const y3 = cy + (1 / 3) * h;
        return <polygon points={`${x1},${y1} ${x2},${y2} ${x3},${y3}`} fill={color} />;
      }

      case 'star': {
        // 五角星
        const R = size / 2;
        const r = R * 0.42;
        const points = [];
        for (let i = 0; i < 10; i++) {
          const radius = i % 2 === 0 ? R : r;
          const angle = (i * 36 - 90) * (Math.PI / 180);
          points.push(`${cx + radius * Math.cos(angle)},${cy + radius * Math.sin(angle)}`);
        }
        return <polygon points={points.join(' ')} fill={color} />;
      }

      case 'diamond': {
        // 菱形
        const hw = size / 2;
        const hh = size * 0.6;
        return (
          <polygon
            points={`${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`}
            fill={color}
          />
        );
      }

      default:
        return <circle cx={cx} cy={cy} r={size / 2} fill={color} />;
    }
  };

  return (
    <div style={{
      backgroundColor: 'rgba(15, 23, 42, 0.6)',
      border: isVerified ? '1px solid rgba(34, 197, 94, 0.4)' : (shake ? '1px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(255, 255, 255, 0.1)'),
      borderRadius: '10px',
      padding: '12px 14px',
      transition: 'all 0.25s ease',
      transform: shake ? 'translateX(-4px)' : 'none'
    }}>
      {/* 顶部标题与刷新按钮 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '10px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          fontWeight: 500,
          color: isVerified ? '#4ade80' : (shake ? '#f87171' : '#94a3b8')
        }}>
          {isVerified ? (
            <CheckCircle2 size={14} color="#4ade80" />
          ) : (
            <Sparkles size={13} color="#38bdf8" />
          )}
          <span>{statusMessage}</span>
        </div>

        {!isVerified && (
          <button
            type="button"
            onClick={generateCaptcha}
            title="更换一组图形"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '2px 4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              borderRadius: '4px',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#38bdf8')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
          >
            <RotateCw size={12} />
            <span>换一组</span>
          </button>
        )}
      </div>

      {/* 4 个形状候选展示区 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px',
      }}>
        {shapes.map((shape, idx) => {
          const isSelected = selectedIndex === idx;
          const isSuccessShape = isVerified && shape.isSmallest;

          return (
            <button
              key={shape.id}
              type="button"
              data-testid="captcha-shape-item"
              data-shape-size={shape.size}
              data-is-smallest={shape.isSmallest ? "true" : "false"}
              disabled={isVerified}
              onClick={() => handleShapeClick(shape, idx)}
              style={{
                height: '62px',
                background: isSuccessShape
                  ? 'rgba(34, 197, 94, 0.15)'
                  : isSelected && !shape.isSmallest
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(255, 255, 255, 0.03)',
                border: isSuccessShape
                  ? '1.5px solid #22c55e'
                  : isSelected && !shape.isSmallest
                  ? '1.5px solid #ef4444'
                  : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: isVerified ? 'default' : 'pointer',
                transition: 'all 0.18s ease',
                padding: 0,
                position: 'relative'
              }}
              onMouseEnter={(e) => {
                if (!isVerified) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                  e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isVerified) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                  e.currentTarget.style.transform = 'none';
                }
              }}
            >
              <svg width="56" height="56" viewBox="0 0 56 56" style={{ overflow: 'visible' }}>
                {renderShapeSvg(shape)}
              </svg>

              {/* 成功标记小角标 */}
              {isSuccessShape && (
                <div style={{
                  position: 'absolute',
                  top: '3px',
                  right: '3px',
                  width: '14px',
                  height: '14px',
                  borderRadius: '50%',
                  background: '#22c55e',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <CheckCircle2 size={10} color="#ffffff" />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
