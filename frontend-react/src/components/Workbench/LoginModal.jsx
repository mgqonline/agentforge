import React, { useState } from 'react';
import { Lock, User, Key, Check, ShieldAlert, Zap, LogIn, Eye, EyeOff } from 'lucide-react';

export default function LoginModal({
  isOpen,
  onClose,
  onLoginSuccess = () => {},
  currentTenantId = 'tenant_enterprise_core',
}) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('AgentForge@2026');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const quickAccounts = [
    {
      title: '👑 超级管理员 (最高权限)',
      user: 'admin',
      pass: 'AgentForge@2026',
      role: 'ADMIN',
      desc: '最高系统权限：可管理用户、修改角色、扩容充值 Token 预算，运行任意代码',
      tenantId: 'tenant_enterprise_core',
      color: '#fbbf24'
    },
    {
      title: '🛠️ AI 架构研发负责人',
      user: 'dev_lead',
      pass: 'Dev@2026',
      role: 'DEVELOPER',
      desc: '研发权限：可执行沙箱代码、评测关卡用例，无法修改租户账单与团队角色',
      tenantId: 'tenant_enterprise_core',
      color: '#60a5fa'
    },
    {
      title: '🔬 算法科学家 (实验室)',
      user: 'researcher',
      pass: 'Lab@2026',
      role: 'DEVELOPER',
      desc: '所属创新算法实验室，独立 Token 配额与隔离沙箱',
      tenantId: 'tenant_algorithm_lab',
      color: '#a78bfa'
    },
    {
      title: '👁️ 只读访客 (受限体验)',
      user: 'guest',
      pass: 'Guest@2026',
      role: 'VIEWER',
      desc: '只读权限：无权执行沙箱代码，极易体验安全策略拦截与熔断效果',
      tenantId: 'tenant_guest_sandbox',
      color: '#94a3b8'
    },
  ];

  const handleLogin = async (targetUser = username, targetPass = password, targetTenant = currentTenantId) => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: targetUser,
          password: targetPass,
          target_tenant_id: targetTenant,
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        localStorage.setItem('agentforge_jwt_token', data.token);
        localStorage.setItem('agentforge_auth_user', JSON.stringify(data.user));
        localStorage.setItem('agentforge_auth_tenant', JSON.stringify(data.tenant));
        localStorage.setItem('agentforge_auth_permissions', JSON.stringify(data.permissions));
        onLoginSuccess(data);
        onClose();
      } else {
        setError(data.detail || '登录失败，请检查账号密码');
      }
    } catch (e) {
      setError('网络连接异常');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--wb-bg-card, #161922)',
        border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.12))',
        borderRadius: '12px',
        width: '560px',
        maxWidth: '95vw',
        padding: '24px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'rgba(59, 130, 246, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--wb-accent-primary, #3b82f6)'
            }}>
              <Lock size={15} />
            </div>
            <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright, #fff)' }}>
              多租户身份登录与极速切换
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--wb-text-dim, #888)',
              fontSize: '18px',
              cursor: 'pointer'
            }}
          >
            ✕
          </button>
        </div>

        {error && (
          <div style={{
            padding: '8px 12px',
            borderRadius: '6px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: '12px',
            marginBottom: '14px'
          }}>
            {error}
          </div>
        )}

        {/* 快速一键免密打靶切换 */}
        <div style={{ marginBottom: '18px' }}>
          <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim, #888)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Zap size={12} color="#fbbf24" />
            <span>快捷体验账号 (点击直接一键切换体验权限差异)：</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {quickAccounts.map((acc) => (
              <button
                key={acc.user}
                onClick={() => {
                  setUsername(acc.user);
                  setPassword(acc.pass);
                  handleLogin(acc.user, acc.pass, acc.tenantId);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.07)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
              >
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: acc.color }}>
                    {acc.title}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', marginTop: '2px' }}>
                    {acc.desc}
                  </div>
                </div>
                <span style={{
                  fontSize: '10.5px',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: 'rgba(255,255,255,0.06)',
                  color: '#aaa',
                  fontFamily: 'monospace'
                }}>
                  一键登录 →
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* 手动输入账密登录 */}
        <form onSubmit={(e) => { e.preventDefault(); handleLogin(); }} style={{
          borderTop: '1px solid rgba(255,255,255,0.08)',
          paddingTop: '14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', display: 'block', marginBottom: '4px' }}>账号用户名</label>
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0 10px' }}>
              <User size={13} color="#888" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#fff',
                  fontSize: '12.5px',
                  padding: '8px 8px',
                  flex: 1
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', display: 'block', marginBottom: '4px' }}>登录密码</label>
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0 8px 0 10px' }}>
              <Key size={13} color="#888" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#fff',
                  fontSize: '12.5px',
                  padding: '8px 8px',
                  flex: 1
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? '隐藏密码' : '显示密码'}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: showPassword ? '#38bdf8' : '#888',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '2px',
                  borderRadius: '4px'
                }}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '6px',
              background: 'var(--wb-accent-primary, #3b82f6)',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              padding: '8px',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <LogIn size={13} />
            <span>{loading ? '正在鉴权验签...' : '立即登录'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
