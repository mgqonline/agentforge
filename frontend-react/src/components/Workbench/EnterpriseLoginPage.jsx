import React, { useState, useEffect } from 'react';
import { User, Key, Zap, LogIn, ShieldAlert, Eye, EyeOff, ShieldCheck, Check } from 'lucide-react';
import ShapeCaptcha from './ShapeCaptcha';

export default function EnterpriseLoginPage({ onLoginSuccess = () => {} }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [captchaVerified, setCaptchaVerified] = useState(false);
  const [captchaResetTrigger, setCaptchaResetTrigger] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 1. 初始化读取记住的密码凭据
  useEffect(() => {
    try {
      const saved = localStorage.getItem('agentforge_remembered_creds');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.username) setUsername(parsed.username);
        if (parsed.password) setPassword(parsed.password);
        setRememberMe(true);
      }
    } catch (e) {
      console.warn('读取本地记住的凭据失败:', e);
    }
  }, []);

  // 快捷体验账号填充
  const handleFillAccount = (user, pass) => {
    setUsername(user);
    setPassword(pass);
    setError('');
  };

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码');
      return;
    }

    // 2. 强制校验图形验证码人机验证
    if (!captchaVerified) {
      setError('请先点击选择最小图形完成人机安全验证');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password.trim(),
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        // 3. 处理记住密码逻辑
        try {
          if (rememberMe) {
            localStorage.setItem('agentforge_remembered_creds', JSON.stringify({
              username: username.trim(),
              password: password.trim()
            }));
          } else {
            localStorage.removeItem('agentforge_remembered_creds');
          }
        } catch (storageErr) {
          console.warn('写入本地记住凭据失败:', storageErr);
        }

        // 保存鉴权状态并回调
        localStorage.setItem('agentforge_jwt_token', data.token);
        localStorage.setItem('agentforge_auth_user', JSON.stringify(data.user));
        localStorage.setItem('agentforge_auth_tenant', JSON.stringify(data.tenant));
        localStorage.setItem('agentforge_auth_permissions', JSON.stringify(data.permissions));
        onLoginSuccess(data);
      } else {
        setError(data.detail || '账号或密码有误，请重新输入');
        // 登录失败防暴力破解：强制刷新图形验证码
        setCaptchaVerified(false);
        setCaptchaResetTrigger(prev => prev + 1);
      }
    } catch (e) {
      setError('连接认证中枢失败，请确认后端服务运行中');
      setCaptchaVerified(false);
      setCaptchaResetTrigger(prev => prev + 1);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100vw',
      backgroundColor: '#0c0e14',
      backgroundImage: 'radial-gradient(ellipse at 50% 15%, rgba(30, 58, 138, 0.15) 0%, transparent 70%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 16px',
      color: '#e2e8f0',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      boxSizing: 'border-box'
    }}>
      {/* 居中核心卡片 */}
      <div style={{
        width: '430px',
        maxWidth: '100%',
        backgroundColor: 'rgba(20, 24, 33, 0.85)',
        border: '1px solid rgba(255, 255, 255, 0.09)',
        borderRadius: '16px',
        padding: '32px 28px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        {/* 顶部品牌区 */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '44px',
            height: '44px',
            margin: '0 auto 12px auto',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 20px rgba(37, 99, 235, 0.35)'
          }}>
            <Zap size={24} color="#ffffff" />
          </div>
          <h1 style={{
            fontSize: '21px',
            fontWeight: 700,
            margin: '0 0 6px 0',
            color: '#f8fafc',
            letterSpacing: '-0.3px'
          }}>
            AgentForge · 智炼工坊
          </h1>
          <p style={{
            fontSize: '13px',
            color: '#94a3b8',
            margin: 0,
            lineHeight: 1.4
          }}>
            企业级 AI 工程架构与智能体实战攻防工坊
          </p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div style={{
            padding: '10px 14px',
            borderRadius: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <ShieldAlert size={14} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* 账号密码表单 */}
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {/* 用户名 */}
          <div>
            <label style={{ fontSize: '12px', color: '#cbd5e1', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
              用户名 / 账号
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              padding: '0 12px',
              transition: 'border-color 0.2s'
            }}>
              <User size={15} color="#64748b" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名 (如 admin)"
                autoFocus
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#fff',
                  padding: '10px',
                  fontSize: '13px'
                }}
              />
            </div>
          </div>

          {/* 密码 */}
          <div>
            <label style={{ fontSize: '12px', color: '#cbd5e1', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
              登录密码
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              padding: '0 10px 0 12px',
              transition: 'border-color 0.2s'
            }}>
              <Key size={15} color="#64748b" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#fff',
                  padding: '10px',
                  fontSize: '13px'
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? '隐藏密码' : '显示密码'}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: showPassword ? '#38bdf8' : '#64748b',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '4px',
                  borderRadius: '4px',
                  transition: 'color 0.2s, background-color 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = showPassword ? '#38bdf8' : '#cbd5e1';
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = showPassword ? '#38bdf8' : '#64748b';
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* 记住密码选项 */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '2px 0'
          }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                userSelect: 'none',
                fontSize: '12px',
                color: '#cbd5e1'
              }}
            >
              <div
                onClick={() => setRememberMe(!rememberMe)}
                style={{
                  width: '16px',
                  height: '16px',
                  borderRadius: '4px',
                  border: rememberMe ? '1px solid #2563eb' : '1px solid rgba(255, 255, 255, 0.25)',
                  backgroundColor: rememberMe ? '#2563eb' : 'rgba(0, 0, 0, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.18s ease'
                }}
              >
                {rememberMe && <Check size={11} color="#ffffff" strokeWidth={3} />}
              </div>
              <span onClick={() => setRememberMe(!rememberMe)}>记住密码</span>
            </label>

            {/* 快速填充体验凭据 */}
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#64748b' }}>快速填入:</span>
              <button
                type="button"
                onClick={() => handleFillAccount('admin', 'AgentForge@2026')}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  color: '#38bdf8',
                  fontSize: '10.5px',
                  padding: '1px 6px',
                  cursor: 'pointer'
                }}
              >
                管理员
              </button>
              <button
                type="button"
                onClick={() => handleFillAccount('dev_lead', 'Dev@2026')}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  color: '#a78bfa',
                  fontSize: '10.5px',
                  padding: '1px 6px',
                  cursor: 'pointer'
                }}
              >
                研发负责人
              </button>
            </div>
          </div>

          {/* 图形验证码：用户必须判断并选择最小的图形 */}
          <div>
            <ShapeCaptcha
              onVerify={(isPassed) => {
                setCaptchaVerified(isPassed);
                if (isPassed) setError('');
              }}
              isVerified={captchaVerified}
              resetTrigger={captchaResetTrigger}
            />
          </div>

          {/* 登录提交按钮 */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '4px',
              backgroundColor: '#2563eb',
              border: 'none',
              borderRadius: '8px',
              color: '#ffffff',
              padding: '11px',
              fontSize: '13.5px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'background-color 0.2s',
              opacity: loading ? 0.8 : 1,
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)'
            }}
            onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#1d4ed8'; }}
            onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#2563eb'; }}
          >
            <LogIn size={15} />
            <span>{loading ? '正在验证身份...' : '登录进入实战台'}</span>
          </button>
        </form>

        {/* 底部极简提示 */}
        <div style={{
          paddingTop: '6px',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          textAlign: 'center',
          fontSize: '11px',
          color: '#64748b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px'
        }}>
          <ShieldCheck size={13} color="#4ade80" />
          <span>多租户安全隔离 · 行为审计与人机防刷已启用</span>
        </div>
      </div>

      {/* 极简版权 */}
      <div style={{
        marginTop: '20px',
        fontSize: '11px',
        color: '#475569',
        textAlign: 'center'
      }}>
        © 2026 AgentForge · 掌握从 Prompt 到企业级多智能体协同生产架构
      </div>
    </div>
  );
}
