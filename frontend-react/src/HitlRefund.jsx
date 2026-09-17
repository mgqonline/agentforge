import React, { useState } from 'react';
import './HitlRefund.css';

const API_BASE = "http://localhost:8081";

export default function HitlRefund() {
  const [threadId] = useState("task_" + Math.random().toString(36).substr(2, 9));
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isPendingApproval, setIsPendingApproval] = useState(false);
  const [approvalMsg, setApprovalMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const appendMsg = (role, text) => {
    setMessages(prev => [...prev, { role, text }]);
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    
    appendMsg('user', inputValue);
    const textToSend = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, message: textToSend })
      });
      const data = await res.json();
      
      if (data.status === 'pending_approval') {
        appendMsg('system', data.message);
        setIsPendingApproval(true);
        setApprovalMsg(data.message);
      } else {
        appendMsg('agent', data.message);
      }
    } catch (e) {
      appendMsg('system', '请求后端失败，请确保 backend/refund_hitl_server.py 正在运行 (端口 8081)。');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproval = async (isApproved) => {
    setIsPendingApproval(false);
    appendMsg('system', isApproved ? '主管已批准，正在唤醒 Agent...' : '主管已驳回请求。');
    
    if (!isApproved) return;

    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, approved: isApproved })
      });
      const data = await res.json();
      
      if (data.status === 'completed') {
        appendMsg('agent', data.message);
      } else {
        appendMsg('system', data.message);
      }
    } catch (e) {
      appendMsg('system', '审批恢复失败。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="hitl-container">
      <h2>🤖 自动化客服 Agent (带有 HITL 拦截) - React 版</h2>
      <p>当前 Thread ID: <span>{threadId}</span></p>
      
      <div className="chat-box">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>
      
      <div className="input-area">
        <input 
          type="text" 
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="请输入你的请求（例如：我的订单 9527 坏了，帮我退款 100 元）..."
          disabled={isLoading || isPendingApproval}
        />
        <button 
          onClick={handleSend} 
          disabled={isLoading || isPendingApproval}
        >
          {isLoading ? '发送中...' : '发送请求'}
        </button>
      </div>

      {isPendingApproval && (
        <div className="approval-panel">
          <h3>🚨 【主管后台端】检测到高危权限请求！</h3>
          <p>{approvalMsg}</p>
          <div className="approval-buttons">
            <button className="btn-approve" onClick={() => handleApproval(true)}>✅ 批准执行</button>
            <button className="btn-reject" onClick={() => handleApproval(false)}>❌ 驳回请求</button>
          </div>
        </div>
      )}
    </div>
  );
}
