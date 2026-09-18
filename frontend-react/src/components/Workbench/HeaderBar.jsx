import React, { useState, useEffect, useRef } from 'react';
import { 
  CheckCircle2, Search, LayoutGrid, Code2, 
  PanelLeft, PanelRight, Maximize2, Trophy,
  Building2, ShieldCheck, Zap, User, ChevronDown,
  LogOut, Palette, Check, Database, Cpu, Network,
  AlertTriangle, RotateCcw, Activity
} from 'lucide-react';
import ThemeSwitcher from './ThemeSwitcher';

export default function HeaderBar({ 
  completedCount = 0, 
  totalPhases = 24, 
  sandboxReady = true,
  currentMode = 'workbench',
  sidebarCollapsed = false,
  guideCollapsed = false,
  currentTheme = 'obsidian',
  currentTenant = null,
  currentUser = null,
  tenantsList = [],
  onSwitchTenant = () => {},
  onOpenGovernance = () => {},
  onOpenKnowledge = () => {},
  onOpenLogin = () => {},
  onLogout = () => {},
  onSelectTheme = () => {},
  onToggleSidebar = () => {},
  onToggleGuide = () => {},
  onToggleZen = () => {},
  setMode = () => {},
  onOpenSearch = () => {},
  onOpenReport = () => {}
}) {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef(null);
  const [isTenantMenuOpen, setIsTenantMenuOpen] = useState(false);
  const tenantMenuRef = useRef(null);
  const [modelCluster, setModelCluster] = useState(null);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const modelMenuRef = useRef(null);
  const [pingLatencies, setPingLatencies] = useState({}); // { [nodeId]: latency_ms }
  const [isPinging, setIsPinging] = useState(false);
  const [isDrilling, setIsDrilling] = useState(false);

  const fetchModelStatus = async () => {
    try {
      const res = await fetch('/api/v1/models/status');
      const data = await res.json();
      if (data.status === 'success') {
        setModelCluster(data.cluster);
      }
    } catch (e) {
      // 静默降级
    }
  };

  useEffect(() => {
    fetchModelStatus();
    const timer = setInterval(fetchModelStatus, 12000);
    return () => clearInterval(timer);
  }, []);

  // 线路健康与连通性测速
  const handlePingNode = async (nodeId) => {
    setIsPinging(true);
    try {
      const res = await fetch('/api/v1/models/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: nodeId })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setPingLatencies(prev => ({
          ...prev,
          [nodeId]: data.ping.latency_ms
        }));
      }
    } catch (e) {
      setPingLatencies(prev => ({ ...prev, [nodeId]: -1 }));
    } finally {
      setIsPinging(false);
    }
  };

  // 故障演练注入 / 恢复
  const handleToggleFault = async (nodeId, shouldFault) => {
    setIsDrilling(true);
    try {
      const res = await fetch('/api/v1/models/inject-fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: nodeId,
          fault_type: shouldFault ? 'force_open' : 'recover',
          duration_seconds: 60
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await fetchModelStatus();
      }
    } catch (e) {
      console.error('Fault drill failed:', e);
    } finally {
      setIsDrilling(false);
    }
  };

  // 点击外部自动收起下拉菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setIsUserMenuOpen(false);
      }
      if (tenantMenuRef.current && !tenantMenuRef.current.contains(event.target)) {
        setIsTenantMenuOpen(false);
      }
      if (modelMenuRef.current && !modelMenuRef.current.contains(event.target)) {
        setIsModelMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  const percent = Math.round((completedCount / (totalPhases || 1)) * 100);

  return (
    <header className="wb-header">
      {/* Brand & 布局折叠控制 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ 
            fontWeight: 700, 
            fontSize: '13.5px', 
            color: 'var(--wb-text-bright)', 
            letterSpacing: '-0.3px', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px' 
          }}>
            <span style={{ color: 'var(--wb-accent-primary)' }}>⚡</span>
            <span>AgentForge</span>
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--wb-text-dim)',
            fontWeight: 500,
            borderLeft: '1px solid var(--wb-border-subtle)',
            paddingLeft: '8px'
          }}>
            智炼工坊
          </span>
          <span style={{
            fontSize: '9px',
            padding: '1px 5px',
            borderRadius: '4px',
            background: 'rgba(59, 130, 246, 0.1)',
            color: 'var(--wb-accent-primary)',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            fontWeight: 600,
            letterSpacing: '0.4px'
          }}>
            STUDIO
          </span>
        </div>

        {/* 分栏视图折叠 */}
        {currentMode === 'workbench' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', marginLeft: '6px' }}>
            <button
              onClick={onToggleSidebar}
              className="wb-btn-ghost"
              style={{
                padding: '3px 6px',
                color: sidebarCollapsed ? 'var(--wb-text-dim)' : 'var(--wb-text-bright)',
                background: sidebarCollapsed ? 'transparent' : 'var(--wb-bg-subtle)'
              }}
              title={sidebarCollapsed ? '展开关卡列表' : '收起关卡列表'}
            >
              <PanelLeft size={13} />
            </button>

            <button
              onClick={onToggleGuide}
              className="wb-btn-ghost"
              style={{
                padding: '3px 6px',
                color: guideCollapsed ? 'var(--wb-text-dim)' : 'var(--wb-text-bright)',
                background: guideCollapsed ? 'transparent' : 'var(--wb-bg-subtle)'
              }}
              title={guideCollapsed ? '展开指导书' : '收起指导书'}
            >
              <PanelRight size={13} />
            </button>

            <button
              onClick={onToggleZen}
              className="wb-btn-ghost"
              style={{
                padding: '3px 6px',
                color: (sidebarCollapsed && guideCollapsed) ? 'var(--wb-accent-subtle)' : 'var(--wb-text-dim)'
              }}
              title="Zen 全屏专注模式 (代码最大化)"
            >
              <Maximize2 size={13} />
            </button>
          </div>
        )}
      </div>

      {/* 中间快捷检索与进度 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button 
          onClick={onOpenSearch}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--wb-bg-subtle)',
            border: '1px solid var(--wb-border-subtle)',
            padding: '3px 10px',
            borderRadius: '5px',
            color: 'var(--wb-text-sub)',
            fontSize: '12px',
            cursor: 'pointer'
          }}
          title="快捷搜索关卡 (快捷键 ⌘K)"
        >
          <Search size={12} />
          <span>跳转关卡...</span>
          <kbd style={{
            fontSize: '10px',
            background: 'var(--wb-bg-hover)',
            padding: '1px 4px',
            borderRadius: '3px',
            color: 'var(--wb-text-dim)'
          }}>⌘K</kbd>
        </button>

        {/* 极简进度指示 */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '6px', 
          fontSize: '11.5px',
          color: 'var(--wb-text-dim)'
        }}>
          <span>{completedCount}/{totalPhases}</span>
          <div style={{
            width: '40px',
            height: '4px',
            borderRadius: '2px',
            background: 'var(--wb-border-subtle)',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${percent}%`,
              height: '100%',
              background: 'var(--wb-accent-success)',
              transition: 'width 0.2s ease'
            }} />
          </div>
        </div>
      </div>

      {/* 右侧：1. 租户算力胶囊  2. 沙箱与模式  3. 个人中心下拉菜单 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* 1. 企业租户与算力微胶囊 (Tenant & Token Budget Capsule) */}
        {currentTenant && (
          <div ref={tenantMenuRef} style={{ position: 'relative' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--wb-bg-subtle, rgba(255, 255, 255, 0.04))',
              border: `1px solid ${currentTenant.is_exhausted ? 'rgba(239, 68, 68, 0.5)' : 'var(--wb-border-subtle, rgba(255, 255, 255, 0.1))'}`,
              borderRadius: '6px',
              padding: '2px 8px',
              gap: '8px',
              fontSize: '11px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.2)'
            }}>
              {/* 租户选择触发器 */}
              <div 
                onClick={() => setIsTenantMenuOpen(!isTenantMenuOpen)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px',
                  cursor: 'pointer',
                  color: 'var(--wb-text-bright, #fff)'
                }}
                title="点击切换组织/租户算力池"
              >
                <Building2 size={12} color="var(--wb-accent-primary, #3b82f6)" />
                <span style={{ fontWeight: 600, maxWidth: '130px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {currentTenant.tenant_name?.split(' ')[0] || '企业核心智算中心'}
                </span>
                <ChevronDown size={11} color="var(--wb-text-dim, #888)" />
              </div>

              {/* 分隔线 */}
              <span style={{ color: 'var(--wb-border-subtle, rgba(255,255,255,0.15))' }}>|</span>

              {/* Token 预算指示 */}
              <div 
                onClick={onOpenGovernance}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer',
                  color: currentTenant.is_exhausted ? '#f87171' : 'var(--wb-text-dim, #94a3b8)'
                }}
                title="点击查看 Token 预算与权限治理中心"
              >
                <Zap size={11} color={currentTenant.is_exhausted ? '#ef4444' : '#fbbf24'} />
                <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>
                  {Math.round((currentTenant.tokens_consumed || 0) / 1000)}k/{Math.round((currentTenant.monthly_token_budget || 0) / 1000)}k
                </span>
                {currentTenant.is_exhausted && (
                  <span style={{ fontSize: '9px', fontWeight: 700, color: '#f87171', background: 'rgba(239, 68, 68, 0.2)', padding: '0 3px', borderRadius: '3px' }}>
                    熔断
                  </span>
                )}
              </div>
            </div>

            {/* 租户业务价值与算力切换下拉浮层 */}
            {isTenantMenuOpen && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                left: 0,
                width: '320px',
                background: 'var(--wb-bg-elevated, #161922)',
                border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.12))',
                borderRadius: '10px',
                boxShadow: '0 12px 30px rgba(0,0,0,0.6)',
                zIndex: 1000,
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--wb-text-bright, #fff)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Building2 size={13} color="var(--wb-accent-primary, #3b82f6)" />
                    <span>多租户算力池切换</span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--wb-text-dim, #888)' }}>
                    {tenantsList.length || 3} 个可用组织
                  </span>
                </div>

                {/* 租户卡片列表 */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '260px', overflowY: 'auto' }}>
                  {(tenantsList.length > 0 ? tenantsList : [
                    { tenant_id: 'tenant_enterprise_core', tenant_name: '企业核心智算中心', max_qps: 50, monthly_token_budget: 2000000, tokens_consumed: 142500 },
                    { tenant_id: 'tenant_algorithm_lab', tenant_name: '创新算法实验室', max_qps: 20, monthly_token_budget: 500000, tokens_consumed: 85200 },
                    { tenant_id: 'tenant_guest_sandbox', tenant_name: '体验试用租户', max_qps: 2, monthly_token_budget: 10000, tokens_consumed: 9850 }
                  ]).map((t) => {
                    const isSelected = (currentTenant?.tenant_id === t.tenant_id);
                    const remaining = Math.max(0, (t.monthly_token_budget || 0) - (t.tokens_consumed || 0));
                    const percentUsed = Math.min(100, Math.round(((t.tokens_consumed || 0) / (t.monthly_token_budget || 1)) * 100));
                    const isNearLimit = remaining <= 200;

                    let tagLabel = '主算力集群 · 50 QPS';
                    let tagColor = '#60a5fa';
                    if (t.tenant_id.includes('lab')) {
                      tagLabel = '算法隔离池 · 20 QPS';
                      tagColor = '#a78bfa';
                    } else if (t.tenant_id.includes('guest')) {
                      tagLabel = '只读测试池 · 2 QPS (熔断演练)';
                      tagColor = '#f87171';
                    }

                    return (
                      <div
                        key={t.tenant_id}
                        onClick={() => {
                          onSwitchTenant(t.tenant_id);
                          setIsTenantMenuOpen(false);
                        }}
                        style={{
                          padding: '8px 10px',
                          borderRadius: '6px',
                          background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${isSelected ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.06)'}`,
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '4px',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '11.5px', fontWeight: 600, color: isSelected ? '#fff' : 'var(--wb-text-bright, #eee)' }}>
                            {t.tenant_name}
                          </span>
                          {isSelected && (
                            <span style={{ fontSize: '10px', color: '#4ade80', fontWeight: 600 }}>● 当前生效</span>
                          )}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10px', color: 'var(--wb-text-dim, #888)' }}>
                          <span style={{ color: tagColor, fontWeight: 500 }}>{tagLabel}</span>
                          <span style={{ fontFamily: 'monospace', color: isNearLimit ? '#f87171' : 'var(--wb-text-sub, #bbb)' }}>
                            剩 {remaining.toLocaleString()} Tokens ({100 - percentUsed}%)
                          </span>
                        </div>

                        {/* 水位进度条 */}
                        <div style={{ width: '100%', height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${percentUsed}%`,
                            height: '100%',
                            background: isNearLimit ? '#ef4444' : percentUsed > 80 ? '#fbbf24' : '#3b82f6',
                            transition: 'width 0.2s'
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* 底部业务作用提示 */}
                <div style={{
                  padding: '6px 8px',
                  borderRadius: '4px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  fontSize: '10px',
                  color: 'var(--wb-text-dim, #888)',
                  lineHeight: 1.4,
                  borderTop: '1px solid rgba(255, 255, 255, 0.05)'
                }}>
                  💡 <strong>业务作用</strong>：切换租户将直接变更当前代码沙箱与 Agent 的<strong>算力扣减归属池</strong>、<strong>并发 QPS 限流门禁</strong>与<strong>独立计费账单</strong>，各租户间算力完全物理隔离。
                </div>
              </div>
            )}
          </div>
        )}

        {/* 2. 沙箱指示点与视图切换 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* 沙箱状态 */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '4px', 
            fontSize: '11px', 
            color: sandboxReady ? 'var(--wb-accent-success, #22c55e)' : 'var(--wb-accent-rose, #f43f5e)' 
          }}
          title={sandboxReady ? '代码执行沙箱正常就绪' : '沙箱离线'}
          >
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: sandboxReady ? 'var(--wb-accent-success, #22c55e)' : 'var(--wb-accent-rose, #f43f5e)'
            }} />
            <span style={{ color: 'var(--wb-text-dim, #888)' }}>沙箱</span>
          </div>

          {/* 模式分段器 */}
          <div style={{
            display: 'flex',
            background: 'var(--wb-bg-subtle, rgba(255, 255, 255, 0.04))',
            padding: '2px',
            borderRadius: '5px',
            border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.1))'
          }}>
            <button
              onClick={() => setMode('workbench')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 7px',
                fontSize: '11px',
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: currentMode === 'workbench' ? 'var(--wb-bg-hover, rgba(255,255,255,0.1))' : 'transparent',
                color: currentMode === 'workbench' ? 'var(--wb-text-bright, #fff)' : 'var(--wb-text-dim, #888)'
              }}
            >
              <Code2 size={11} />
              <span>实战台</span>
            </button>
            <button
              onClick={() => setMode('dashboard')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 7px',
                fontSize: '11px',
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: currentMode === 'dashboard' ? 'var(--wb-bg-hover, rgba(255,255,255,0.1))' : 'transparent',
                color: currentMode === 'dashboard' ? 'var(--wb-text-bright, #fff)' : 'var(--wb-text-dim, #888)'
              }}
            >
              <LayoutGrid size={11} />
              <span>概览</span>
            </button>
          </div>

          {/* 知识库入口 */}
          <button
            onClick={onOpenKnowledge}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '3px 9px',
              borderRadius: '5px',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              background: 'rgba(59, 130, 246, 0.08)',
              color: '#60a5fa',
              fontSize: '11.5px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
            title="打开企业私有知识库 (RAG & 文档解析)"
          >
            <Database size={12} />
            <span>知识库</span>
          </button>

          {/* 高可用模型集群状态指示微胶囊 (Circuit Breaker Indicator) */}
          {modelCluster && (
            <div ref={modelMenuRef} style={{ position: 'relative' }}>
              <div
                onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 8px',
                  borderRadius: '5px',
                  border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.1))',
                  background: 'var(--wb-bg-subtle, rgba(255, 255, 255, 0.04))',
                  color: modelCluster.cluster_health === 'healthy' ? '#4ade80' : '#f59e0b',
                  fontSize: '11px',
                  cursor: 'pointer'
                }}
                title="点击查看大模型高可用多路熔断路由状态"
              >
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: modelCluster.cluster_health === 'healthy' ? '#22c55e' : '#f59e0b',
                  boxShadow: modelCluster.cluster_health === 'healthy' ? '0 0 6px #22c55e' : 'none'
                }} />
                <Cpu size={11} />
                <span style={{ color: 'var(--wb-text-bright, #fff)', fontWeight: 500 }}>
                  {modelCluster.nodes?.[0]?.name?.split(' ')[0] || 'DeepSeek'}
                </span>
                <span style={{
                  fontSize: '9.5px',
                  padding: '0 4px',
                  borderRadius: '3px',
                  background: modelCluster.cluster_health === 'healthy' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: modelCluster.cluster_health === 'healthy' ? '#4ade80' : '#f59e0b',
                  fontFamily: 'monospace'
                }}>
                  {modelCluster.nodes?.[0]?.state || 'CLOSED'}
                </span>
              </div>

              {/* 模型路由节点下拉卡片 */}
              {isModelMenuOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  right: 0,
                  width: '320px',
                  background: 'var(--wb-bg-elevated, #161922)',
                  border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.12))',
                  borderRadius: '10px',
                  boxShadow: '0 12px 30px rgba(0,0,0,0.6)',
                  zIndex: 1000,
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--wb-text-bright, #fff)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Network size={13} color="#3b82f6" />
                      <span>LLM 主备倒换与熔断集群</span>
                    </div>
                    <span style={{
                      fontSize: '10px',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: modelCluster.cluster_health === 'healthy' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: modelCluster.cluster_health === 'healthy' ? '#4ade80' : '#f59e0b'
                    }}>
                      集群: {modelCluster.cluster_health.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {modelCluster.nodes?.map(node => {
                      const isFaulted = (node.state === 'OPEN');
                      const latency = pingLatencies[node.id];

                      return (
                        <div key={node.id} style={{
                          background: isFaulted ? 'rgba(239, 68, 68, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${isFaulted ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255, 255, 255, 0.06)'}`,
                          borderRadius: '6px',
                          padding: '8px 10px',
                          fontSize: '11px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ fontWeight: 600, color: 'var(--wb-text-bright, #fff)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                              <span>{node.priority === 1 ? '🥇 主线路: ' : '🥈 备用线路: '}{node.name}</span>
                              {latency !== undefined && (
                                <span style={{
                                  fontSize: '9.5px',
                                  padding: '1px 5px',
                                  borderRadius: '3px',
                                  fontFamily: 'monospace',
                                  background: latency < 0 ? 'rgba(239, 68, 68, 0.2)' : latency < 300 ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                                  color: latency < 0 ? '#f87171' : latency < 300 ? '#4ade80' : '#fbbf24'
                                }}>
                                  {latency < 0 ? '超时' : `${latency}ms`}
                                </span>
                              )}
                            </div>
                            <span style={{
                              fontSize: '9px',
                              padding: '1px 5px',
                              borderRadius: '3px',
                              fontWeight: 600,
                              background: node.state === 'CLOSED' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                              color: node.state === 'CLOSED' ? '#4ade80' : '#f87171'
                            }}>
                              {node.state === 'CLOSED' ? 'NORMAL 闭合' : 'OPEN 熔断断开'}
                            </span>
                          </div>

                          <div style={{ fontSize: '10px', color: 'var(--wb-text-dim, #888)', display: 'flex', justifyContent: 'space-between' }}>
                            <span>模型: {node.model_name}</span>
                            <span>调用: {node.total_calls} 次 (切流: {node.total_fallovers})</span>
                          </div>

                          {/* 交互演练栏：线路测速 + 一键故障注入/恢复 */}
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', paddingTop: '4px', borderTop: '1px dashed rgba(255,255,255,0.06)' }}>
                            <button
                              onClick={() => handlePingNode(node.id)}
                              disabled={isPinging}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px',
                                padding: '2px 7px',
                                borderRadius: '4px',
                                border: '1px solid rgba(59, 130, 246, 0.3)',
                                background: 'rgba(59, 130, 246, 0.1)',
                                color: '#60a5fa',
                                fontSize: '10px',
                                cursor: isPinging ? 'wait' : 'pointer'
                              }}
                              title="对当前线路发起心跳 Ping 测速"
                            >
                              <Activity size={10} />
                              <span>{isPinging ? '测速中...' : '⚡ 线路测速'}</span>
                            </button>

                            <button
                              onClick={() => handleToggleFault(node.id, !isFaulted)}
                              disabled={isDrilling}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px',
                                padding: '2px 7px',
                                borderRadius: '4px',
                                border: `1px solid ${isFaulted ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                background: isFaulted ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                color: isFaulted ? '#4ade80' : '#f87171',
                                fontSize: '10px',
                                cursor: isDrilling ? 'wait' : 'pointer'
                              }}
                              title={isFaulted ? '恢复线路为正常状态' : '模拟注入 429 故障，触发主备自动倒换演练'}
                            >
                              {isFaulted ? <RotateCcw size={10} /> : <AlertTriangle size={10} />}
                              <span>{isFaulted ? '🟢 恢复健康' : '🔴 模拟 429 故障'}</span>
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div style={{
                    fontSize: '10px',
                    color: 'var(--wb-text-dim, #888)',
                    lineHeight: 1.4,
                    paddingTop: '6px',
                    borderTop: '1px solid rgba(255,255,255,0.05)'
                  }}>
                    🛡️ <strong>容灾策略</strong>：遇 429 限流或 5xx 故障时，毫秒级指数退避并无缝倒换至备用线路，保障生产 0 业务中断。
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 3. 用户个人中心下拉菜单 (收敛治理、报告、主题与退出) */}
        <div style={{ position: 'relative' }} ref={userMenuRef}>
          <button
            onClick={() => setIsUserMenuOpen(prev => !prev)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: '6px',
              border: `1px solid ${currentUser?.role === 'admin' ? 'rgba(245, 158, 11, 0.35)' : 'rgba(59, 130, 246, 0.25)'}`,
              background: currentUser?.role === 'admin' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(59, 130, 246, 0.08)',
              color: currentUser?.role === 'admin' ? '#fbbf24' : '#60a5fa',
              cursor: 'pointer',
              fontSize: '11.5px',
              fontWeight: 600,
              boxShadow: '0 1px 2px rgba(0,0,0,0.15)'
            }}
          >
            <User size={12} />
            <span>{currentUser?.role === 'admin' ? '👑 超管' : currentUser?.role === 'developer' ? '🛠️ 研发' : '👁️ 访客'}: {currentUser?.username || 'admin'}</span>
            <ChevronDown size={11} style={{ transform: isUserMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>

          {/* 下拉浮层卡片 */}
          {isUserMenuOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              width: '240px',
              background: 'var(--wb-bg-card, #161922)',
              border: '1px solid var(--wb-border-subtle, rgba(255, 255, 255, 0.12))',
              borderRadius: '10px',
              boxShadow: '0 15px 35px -5px rgba(0, 0, 0, 0.6)',
              zIndex: 9999,
              padding: '6px 0',
              animation: 'fadeIn 0.15s ease-out'
            }}>
              {/* 用户信息标头 */}
              <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--wb-border-subtle, rgba(255,255,255,0.08))' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--wb-text-bright, #fff)' }}>
                  {currentUser?.display_name || currentUser?.username}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--wb-text-dim, #888)', marginTop: '2px' }}>
                  租户: {currentTenant?.tenant_name || '默认租户'}
                </div>
              </div>

              {/* 菜单项 */}
              <div style={{ padding: '4px 0' }}>
                {/* 权限治理 */}
                <button
                  onClick={() => { setIsUserMenuOpen(false); onOpenGovernance(); }}
                  style={{
                    width: '100%',
                    padding: '8px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--wb-accent-primary, #3b82f6)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <ShieldCheck size={14} />
                  <span>权限与租户治理中心</span>
                </button>

                {/* 企业知识库 */}
                <button
                  onClick={() => { setIsUserMenuOpen(false); onOpenKnowledge(); }}
                  style={{
                    width: '100%',
                    padding: '8px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: '#60a5fa',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Database size={14} />
                  <span>企业私有知识库中心</span>
                </button>

                {/* 能力报告 */}
                <button
                  onClick={() => { setIsUserMenuOpen(false); onOpenReport(); }}
                  style={{
                    width: '100%',
                    padding: '8px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--wb-text-bright, #fff)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Trophy size={14} color="#fbbf24" />
                  <span>学员全维能力报告</span>
                </button>

                {/* 界面主题 */}
                <div style={{ padding: '6px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '12px', color: 'var(--wb-text-dim, #888)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Palette size={14} />
                    <span>色彩主题</span>
                  </span>
                  <ThemeSwitcher currentTheme={currentTheme} onSelectTheme={onSelectTheme} />
                </div>
              </div>

              {/* 分隔线 */}
              <div style={{ height: '1px', background: 'var(--wb-border-subtle, rgba(255,255,255,0.08))', margin: '4px 0' }} />

              {/* 切换账号 & 退出登录 */}
              <div style={{ padding: '4px 0' }}>
                <button
                  onClick={() => { setIsUserMenuOpen(false); onOpenLogin(); }}
                  style={{
                    width: '100%',
                    padding: '7px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--wb-text-sub, #aaa)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <User size={13} />
                  <span>切换体验账号...</span>
                </button>

                <button
                  onClick={() => { setIsUserMenuOpen(false); onLogout(); }}
                  style={{
                    width: '100%',
                    padding: '7px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'transparent',
                    border: 'none',
                    color: '#f87171',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <LogOut size={13} />
                  <span>退出系统登录</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
