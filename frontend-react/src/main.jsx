import React, { Component } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[React App Error]", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          backgroundColor: '#0f1117',
          color: '#e2e8f0',
          fontFamily: 'Inter, -apple-system, sans-serif',
          padding: '24px'
        }}>
          <h2 style={{ color: '#f87171', marginBottom: '8px' }}>终端工作区加载遇到异常</h2>
          <p style={{ color: '#94a3b8', maxWidth: '500px', textAlign: 'center', marginBottom: '20px' }}>
            {this.state.error?.message || "发生未知组件渲染异常，已触发保护屏障。"}
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '8px 18px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: '#3b82f6',
                color: '#fff',
                cursor: 'pointer'
              }}
            >
              重新加载
            </button>
            <a
              href="/vanilla/"
              style={{
                padding: '8px 18px',
                borderRadius: '6px',
                border: '1px solid #475569',
                color: '#cbd5e1',
                textDecoration: 'none',
                display: 'inline-block'
              }}
            >
              切换至原生轻量终端
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <GlobalErrorBoundary>
    <App />
  </GlobalErrorBoundary>
);
