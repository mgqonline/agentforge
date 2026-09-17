import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, Users, Key, Sliders, CheckCircle2, 
  XCircle, Plus, RefreshCw, AlertTriangle, Building2, UserCheck, ShieldAlert
} from 'lucide-react';

export default function UserRoleGovernanceModal({
  isOpen,
  onClose,
  currentTenant,
  currentUser,
  onUpdateTenantQuota = () => {},
  onSwitchTenant = () => {},
}) {
  const [activeTab, setActiveTab] = useState('users'); // 'users' | 'roles' | 'budget' | 'audits'
  const [users, setUsers] = useState([]);
  const [rolesMatrix, setRolesMatrix] = useState({});
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // 新增用户表单
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('developer');
  const [newDisplayName, setNewDisplayName] = useState('');

  // 预算调优表单
  const [monthlyBudget, setMonthlyBudget] = useState(
    currentTenant?.monthly_token_budget || 2000000
  );

  useEffect(() => {
    if (currentTenant?.monthly_token_budget) {
      setMonthlyBudget(currentTenant.monthly_token_budget);
    }
  }, [currentTenant]);

  useEffect(() => {
    if (isOpen) {
      loadUsers();
      loadRolesMatrix();
      loadAudits();
    }
  }, [isOpen, currentTenant?.tenant_id]);

  const loadAudits = async () => {
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch('/api/v1/governance/audits', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        }
      });
      const data = await res.json();
      if (data.status === 'success') {
        setAudits(data.audits || []);
      }
    } catch (e) {
      console.error('Failed to load audits:', e);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch('/api/v1/governance/users', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        }
      });
      const data = await res.json();
      if (data.status === 'success') {
        setUsers(data.users || []);
      }
    } catch (e) {
      console.error('Failed to load users:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadRolesMatrix = async () => {
    try {
      const res = await fetch('/api/v1/governance/roles');
      const data = await res.json();
      if (data.status === 'success') {
        setRolesMatrix(data.matrix || {});
      }
    } catch (e) {
      console.error('Failed to load roles matrix:', e);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUsername || !newPassword) {
      setFeedback({ type: 'error', text: '请填写用户名和密码' });
      return;
    }
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch('/api/v1/governance/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
          role: newRole,
          tenant_id: currentTenant?.tenant_id,
          display_name: newDisplayName
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setFeedback({ type: 'success', text: `用户 [${newUsername}] 创建成功，已赋予 [${newRole}] 角色！` });
        setNewUsername('');
        setNewPassword('');
        setNewDisplayName('');
        loadUsers();
      } else {
        setFeedback({ type: 'error', text: data.detail || '创建用户失败' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: '网络请求异常' });
    }
  };

  const handleUpdateRole = async (username, targetRole) => {
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch(`/api/v1/governance/users/${username}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        },
        body: JSON.stringify({ role: targetRole })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setFeedback({ type: 'success', text: `用户 [${username}] 角色已更新为 [${targetRole}]！` });
        loadUsers();
      } else {
        setFeedback({ type: 'error', text: data.detail || '调整角色失败' });
      }
    } catch (e) {
      setFeedback({ type: 'error', text: '网络请求异常' });
    }
  };

  const handleUpdateBudget = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('agentforge_jwt_token');
      const res = await fetch(`/api/v1/governance/tenants/${currentTenant?.tenant_id}/budget`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
          'X-Tenant-Id': currentTenant?.tenant_id || ''
        },
        body: JSON.stringify({ monthly_token_budget: parseInt(monthlyBudget, 10) })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setFeedback({ type: 'success', text: `租户 Token 预算上限已更新为 ${parseInt(monthlyBudget, 10).toLocaleString()} Tokens！` });
        onUpdateTenantQuota(data.tenant);
      } else {
        setFeedback({ type: 'error', text: data.detail || '调整预算失败' });
      }
    } catch (e) {
      setFeedback({ type: 'error', text: '网络请求异常' });
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--wb-bg-card, #161922)',
        border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.12))',
        borderRadius: '12px',
        width: '880px',
        maxWidth: '95vw',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
        overflow: 'hidden'
      }}>
        {/* 头部标题与租户标识 */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(59, 130, 246, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--wb-accent-primary, #3b82f6)'
            }}>
              <ShieldCheck size={18} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--wb-text-bright, #fff)' }}>
                多租户治理与用户权限管理中心 (RBAC Governance)
              </div>
              <div style={{ fontSize: '12px', color: 'var(--wb-text-dim, #888)', display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                <Building2 size={12} />
                <span>当前租户: <strong style={{ color: 'var(--wb-accent-subtle, #60a5fa)' }}>{currentTenant?.tenant_name || '企业核心智算中心'}</strong></span>
                <span>·</span>
                <UserCheck size={12} />
                <span>操作身份: <strong>{currentUser?.display_name || '超级管理员 (Admin)'}</strong></span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--wb-text-dim, #888)',
              fontSize: '18px',
              cursor: 'pointer',
              padding: '4px'
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab 导航切换 */}
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '12px 24px',
          borderBottom: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
          background: 'rgba(0,0,0,0.1)'
        }}>
          <button
            onClick={() => { setActiveTab('users'); setFeedback(null); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12.5px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'users' ? 'var(--wb-accent-primary, #3b82f6)' : 'transparent',
              color: activeTab === 'users' ? '#fff' : 'var(--wb-text-sub, #aaa)'
            }}
          >
            <Users size={14} />
            <span>租户用户管理 ({users.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('roles'); setFeedback(null); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12.5px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'roles' ? 'var(--wb-accent-primary, #3b82f6)' : 'transparent',
              color: activeTab === 'roles' ? '#fff' : 'var(--wb-text-sub, #aaa)'
            }}
          >
            <Key size={14} />
            <span>角色权限矩阵 (RBAC Matrix)</span>
          </button>

          <button
            onClick={() => { setActiveTab('budget'); setFeedback(null); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12.5px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'budget' ? 'var(--wb-accent-primary, #3b82f6)' : 'transparent',
              color: activeTab === 'budget' ? '#fff' : 'var(--wb-text-sub, #aaa)'
            }}
          >
            <Sliders size={14} />
            <span>Token 预算调优与充值</span>
          </button>

          <button
            onClick={() => { setActiveTab('audits'); setFeedback(null); loadAudits(); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              fontSize: '12.5px',
              cursor: 'pointer',
              fontWeight: 500,
              background: activeTab === 'audits' ? 'var(--wb-accent-primary, #3b82f6)' : 'transparent',
              color: activeTab === 'audits' ? '#fff' : 'var(--wb-text-sub, #aaa)'
            }}
          >
            <RefreshCw size={13} />
            <span>用户使用与审计流水 ({audits.length})</span>
          </button>
        </div>

        {/* 动态通知提示栏 */}
        {feedback && (
          <div style={{
            padding: '10px 24px',
            background: feedback.type === 'success' ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            borderBottom: `1px solid ${feedback.type === 'success' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: feedback.type === 'success' ? '#4ade80' : '#f87171',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {feedback.type === 'success' ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* 主内容区域 */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {/* TAB 1: 用户管理 */}
          {activeTab === 'users' && (
            <div>
              {/* 新增用户卡片 */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                borderRadius: '8px',
                padding: '14px 16px',
                marginBottom: '18px'
              }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright, #fff)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Plus size={14} color="var(--wb-accent-primary, #3b82f6)" />
                  <span>为当前租户添加新成员</span>
                </div>
                <form onSubmit={handleCreateUser} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="用户名 (如 alice)"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '5px',
                      padding: '6px 10px',
                      color: '#fff',
                      fontSize: '12px',
                      width: '130px'
                    }}
                  />
                  <input
                    type="password"
                    placeholder="登录初始密码"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '5px',
                      padding: '6px 10px',
                      color: '#fff',
                      fontSize: '12px',
                      width: '130px'
                    }}
                  />
                  <input
                    type="text"
                    placeholder="显示名称 (如 算法工程师)"
                    value={newDisplayName}
                    onChange={(e) => setNewDisplayName(e.target.value)}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '5px',
                      padding: '6px 10px',
                      color: '#fff',
                      fontSize: '12px',
                      width: '140px'
                    }}
                  />
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    style={{
                      background: '#1e2230',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '5px',
                      padding: '6px 10px',
                      color: '#fff',
                      fontSize: '12px'
                    }}
                  >
                    <option value="developer">研发工程师 (Developer)</option>
                    <option value="viewer">只读访客 (Viewer)</option>
                    <option value="admin">超级管理员 (Admin)</option>
                  </select>
                  <button
                    type="submit"
                    style={{
                      background: 'var(--wb-accent-primary, #3b82f6)',
                      border: 'none',
                      borderRadius: '5px',
                      color: '#fff',
                      padding: '6px 14px',
                      fontSize: '12px',
                      cursor: 'pointer',
                      fontWeight: 600
                    }}
                  >
                    + 添加成员
                  </button>
                </form>
              </div>

              {/* 用户列表表格 */}
              <div style={{
                border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--wb-text-dim, #888)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                      <th style={{ padding: '10px 14px' }}>账号 (Username)</th>
                      <th style={{ padding: '10px 14px' }}>姓名/说明</th>
                      <th style={{ padding: '10px 14px' }}>所属租户</th>
                      <th style={{ padding: '10px 14px' }}>当前角色</th>
                      <th style={{ padding: '10px 14px' }}>权限调整 (RBAC)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => {
                      const isAdmin = u.role === 'admin';
                      const isViewer = u.role === 'viewer';
                      return (
                        <tr key={u.user_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--wb-text-bright, #fff)' }}>
                          <td style={{ padding: '10px 14px', fontWeight: 600 }}>
                            <span style={{ color: isAdmin ? '#fbbf24' : isViewer ? '#94a3b8' : '#60a5fa' }}>● </span>
                            {u.username}
                          </td>
                          <td style={{ padding: '10px 14px', color: 'var(--wb-text-sub, #aaa)' }}>{u.display_name}</td>
                          <td style={{ padding: '10px 14px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(255,255,255,0.06)',
                              fontSize: '11px',
                              fontFamily: 'monospace'
                            }}>
                              {u.tenant_id}
                            </span>
                          </td>
                          <td style={{ padding: '10px 14px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 600,
                              fontSize: '11px',
                              background: isAdmin ? 'rgba(245, 158, 11, 0.15)' : isViewer ? 'rgba(148, 163, 184, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                              color: isAdmin ? '#fbbf24' : isViewer ? '#cbd5e1' : '#60a5fa',
                              border: `1px solid ${isAdmin ? 'rgba(245, 158, 11, 0.3)' : isViewer ? 'rgba(148, 163, 184, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`
                            }}>
                              {u.role.toUpperCase()}
                            </span>
                          </td>
                          <td style={{ padding: '10px 14px' }}>
                            <select
                              value={u.role}
                              onChange={(e) => handleUpdateRole(u.username, e.target.value)}
                              disabled={u.username === 'admin'}
                              style={{
                                background: '#1c202d',
                                border: '1px solid rgba(255,255,255,0.15)',
                                color: '#fff',
                                fontSize: '11px',
                                borderRadius: '4px',
                                padding: '4px 6px',
                                cursor: u.username === 'admin' ? 'not-allowed' : 'pointer',
                                opacity: u.username === 'admin' ? 0.6 : 1
                              }}
                            >
                              <option value="admin">Admin (超管)</option>
                              <option value="developer">Developer (研发)</option>
                              <option value="viewer">Viewer (访客只读)</option>
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: 角色权限矩阵 */}
          {activeTab === 'roles' && (
            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--wb-text-sub, #aaa)', marginBottom: '14px' }}>
                企业级统一访问控制矩阵 (Role-Based Access Control) 采用最小特权原则，对算力调用与数据变更进行严格隔离：
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
                {Object.entries(rolesMatrix).map(([roleKey, roleDef]) => {
                  const isAdmin = roleKey === 'admin';
                  const isViewer = roleKey === 'viewer';
                  return (
                    <div key={roleKey} style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isAdmin ? 'rgba(245, 158, 11, 0.3)' : isViewer ? 'rgba(148, 163, 184, 0.2)' : 'rgba(59, 130, 246, 0.3)'}`,
                      borderRadius: '8px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}>
                      <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '10px' }}>
                        <div style={{
                          fontWeight: 700,
                          fontSize: '13.5px',
                          color: isAdmin ? '#fbbf24' : isViewer ? '#cbd5e1' : '#60a5fa'
                        }}>
                          {roleDef.label}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', marginTop: '4px' }}>
                          {roleDef.description}
                        </div>
                      </div>

                      {/* 权限清单 */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {roleDef.permissions?.map((p) => (
                          <div key={p.key} style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '11.5px',
                            color: p.enabled ? 'var(--wb-text-bright, #fff)' : 'var(--wb-text-dim, #666)'
                          }}>
                            <span>{p.name}</span>
                            {p.enabled ? (
                              <span style={{ color: '#4ade80', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                                <CheckCircle2 size={13} /> 允许
                              </span>
                            ) : (
                              <span style={{ color: '#f87171', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                                <XCircle size={13} /> 阻断
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: 租户预算治理 */}
          {activeTab === 'budget' && (
            <div style={{ maxWidth: '600px' }}>
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                borderRadius: '8px',
                padding: '18px',
                marginBottom: '16px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--wb-text-bright, #fff)', marginBottom: '12px' }}>
                  📊 当前租户 Token 预算水位
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12.5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--wb-text-dim, #888)' }}>租户名称:</span>
                    <strong style={{ color: '#fff' }}>{currentTenant?.tenant_name}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--wb-text-dim, #888)' }}>最大并发限流 (QPS):</span>
                    <span style={{ color: '#60a5fa' }}>{currentTenant?.max_qps || 50} 次/秒 (滑动窗口)</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--wb-text-dim, #888)' }}>当月已消耗 Tokens:</span>
                    <span style={{ color: '#fbbf24', fontFamily: 'monospace' }}>
                      {(currentTenant?.tokens_consumed || 0).toLocaleString()} Tokens
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--wb-text-dim, #888)' }}>剩余可用 Tokens:</span>
                    <span style={{
                      color: (currentTenant?.tokens_remaining || 0) <= 500 ? '#f87171' : '#4ade80',
                      fontFamily: 'monospace',
                      fontWeight: 700
                    }}>
                      {(currentTenant?.tokens_remaining || 0).toLocaleString()} Tokens
                    </span>
                  </div>
                </div>

                {/* 预算消耗进度条 */}
                <div style={{ marginTop: '14px' }}>
                  <div style={{
                    height: '8px',
                    borderRadius: '4px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, (currentTenant?.tokens_consumed / (currentTenant?.monthly_token_budget || 1)) * 100)}%`,
                      background: (currentTenant?.tokens_consumed >= currentTenant?.monthly_token_budget) ? '#ef4444' : '#3b82f6',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', marginTop: '4px', textAlign: 'right' }}>
                    使用率: {((currentTenant?.tokens_consumed / (currentTenant?.monthly_token_budget || 1)) * 100).toFixed(1)}%
                    {currentTenant?.is_exhausted && <span style={{ color: '#f87171', marginLeft: '6px' }}>[⚡ 已触发熔断]</span>}
                  </div>
                </div>
              </div>

              {/* 预算调整与充值表单 */}
              <form onSubmit={handleUpdateBudget} style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                borderRadius: '8px',
                padding: '18px'
              }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>
                  ⚡ 调整或充值当月 Token 预算上限
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--wb-text-dim, #888)', marginBottom: '12px' }}>
                  当租户消耗超过此阈值时，网关将自动阻断沙箱代码执行与大模型调用，防范恶意刷量或账单失控。
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="number"
                    step="10000"
                    value={monthlyBudget}
                    onChange={(e) => setMonthlyBudget(e.target.value)}
                    style={{
                      flex: 1,
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#fff',
                      fontSize: '13px',
                      fontFamily: 'monospace'
                    }}
                  />
                  <button
                    type="submit"
                    style={{
                      background: 'var(--wb-accent-primary, #3b82f6)',
                      border: 'none',
                      borderRadius: '6px',
                      color: '#fff',
                      padding: '8px 18px',
                      fontSize: '12.5px',
                      cursor: 'pointer',
                      fontWeight: 600
                    }}
                  >
                    保存并立即生效
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 4: 用户使用行为与审计流水 */}
          {activeTab === 'audits' && (
            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--wb-text-sub, #aaa)', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>实时跟进全系统各租户成员的登录、沙箱调试、通关评测与算力 Token 消耗流水：</span>
                <button
                  onClick={loadAudits}
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '4px',
                    color: '#fff',
                    padding: '3px 8px',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}
                >
                  刷新流水
                </button>
              </div>

              <div style={{
                border: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11.5px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--wb-text-dim, #888)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                      <th style={{ padding: '8px 12px' }}>时间 (Timestamp)</th>
                      <th style={{ padding: '8px 12px' }}>用户 (User)</th>
                      <th style={{ padding: '8px 12px' }}>租户 (Tenant)</th>
                      <th style={{ padding: '8px 12px' }}>动作 (Action)</th>
                      <th style={{ padding: '8px 12px' }}>详细日志 (Details)</th>
                      <th style={{ padding: '8px 12px' }}>Token 消耗</th>
                      <th style={{ padding: '8px 12px' }}>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audits.map((item) => {
                      const isBlocked = item.status === 'blocked' || item.status === 'exhausted';
                      return (
                        <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--wb-text-bright, #fff)' }}>
                          <td style={{ padding: '8px 12px', color: 'var(--wb-text-dim, #888)', fontFamily: 'monospace' }}>{item.timestamp}</td>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{item.username}</td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ fontSize: '10.5px', background: 'rgba(255,255,255,0.05)', padding: '1px 5px', borderRadius: '3px' }}>
                              {item.tenant_id}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{
                              fontSize: '10px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: 600,
                              background: item.action === 'login' ? 'rgba(59, 130, 246, 0.15)' : item.action === 'sandbox_run' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                              color: item.action === 'login' ? '#60a5fa' : item.action === 'sandbox_run' ? '#4ade80' : '#f87171'
                            }}>
                              {item.action.toUpperCase()}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', color: 'var(--wb-text-sub, #aaa)' }}>{item.details}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: item.cost_tokens > 0 ? '#fbbf24' : 'var(--wb-text-dim, #666)' }}>
                            {item.cost_tokens > 0 ? `+${item.cost_tokens}` : '-'}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{ color: isBlocked ? '#f87171' : '#4ade80', fontWeight: 500 }}>
                              {item.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* 底部按钮栏 */}
        <div style={{
          padding: '12px 24px',
          borderTop: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))',
          display: 'flex',
          justifyContent: 'flex-end',
          background: 'rgba(255, 255, 255, 0.01)'
        }}>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              padding: '6px 16px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            完成并关闭
          </button>
        </div>
      </div>
    </div>
  );
}
