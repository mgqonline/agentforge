import React, { useRef, useEffect } from 'react';
import { PanelLeftOpen } from 'lucide-react';
import { Virtuoso } from 'react-virtuoso';
import Message from './Message';
import ChatInput from './ChatInput';

const MainChat = ({ 
  collapsed, 
  setCollapsed, 
  chat, 
  wsStatus, 
  inputText, 
  setInputText, 
  handleSend, 
  handleStop, 
  isStreaming,
  imageBase64,
  setImageBase64,
  faceBase64,
  setFaceBase64,
  audioBase64,
  setAudioBase64,
  fileUpload,
  setFileUpload,
  mode,
  setMode,
  setArtifact,
  setChats,
  wsRef,
  onHitlDecision,
  isAuthenticated,
  onRequireAuth
}) => {
  const virtuosoRef = useRef(null);
  
  // Auto-scroll on new message or when streaming
  useEffect(() => {
    if (chat && chat.messages.length > 0 && virtuosoRef.current) {
      virtuosoRef.current.scrollToIndex({ index: chat.messages.length - 1, align: 'end', behavior: 'auto' });
    }
  }, [chat?.messages.length, chat?.messages[chat?.messages.length - 1]?.content]);

  const messages = chat ? chat.messages : [];

  const handleEditSubmit = (index, newContent) => {
    if (!newContent.trim() || isStreaming) return;
    
    setChats(prev => {
      const newChats = [...prev];
      const chatIdx = newChats.findIndex(c => c.id === chat.id);
      if (chatIdx === -1) return prev;
      
      const targetChat = { ...newChats[chatIdx] };
      const oldMsg = targetChat.messages[index];
      const tail = targetChat.messages.slice(index + 1);
      
      const updatedMsg = { ...oldMsg };
      
      if (!updatedMsg.branches) {
        updatedMsg.branches = [{ content: oldMsg.content, tail: tail }];
        updatedMsg.currentBranch = 0;
      }
      
      updatedMsg.branches.push({ content: newContent, tail: [] });
      updatedMsg.currentBranch = updatedMsg.branches.length - 1;
      updatedMsg.content = newContent;
      
      targetChat.messages = [...targetChat.messages.slice(0, index), updatedMsg];
      newChats[chatIdx] = targetChat;
      return newChats;
    });

    if (wsRef && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const history = chat.messages.slice(0, index).map(m => ({
        role: m.role === 'system' ? 'assistant' : m.role,
        content: m.content
      }));
      
      wsRef.current.send(JSON.stringify({
        message: newContent,
        mode: mode,
        image_data: null, // Edit doesn't carry image right now
        history: history
      }));
    }
  };

  const handleBranchSwitch = (index, direction) => {
    setChats(prev => {
      const newChats = [...prev];
      const chatIdx = newChats.findIndex(c => c.id === chat.id);
      if (chatIdx === -1) return prev;
      
      const targetChat = { ...newChats[chatIdx] };
      const msg = targetChat.messages[index];
      if (!msg.branches) return prev;
      
      const oldBranchIdx = msg.currentBranch;
      let newBranchIdx = oldBranchIdx + direction;
      if (newBranchIdx < 0 || newBranchIdx >= msg.branches.length) return prev;
      
      const updatedMsg = { ...msg };
      
      updatedMsg.branches[oldBranchIdx].tail = targetChat.messages.slice(index + 1);
      updatedMsg.currentBranch = newBranchIdx;
      updatedMsg.content = updatedMsg.branches[newBranchIdx].content;
      
      targetChat.messages = [
        ...targetChat.messages.slice(0, index),
        updatedMsg,
        ...updatedMsg.branches[newBranchIdx].tail
      ];
      
      newChats[chatIdx] = targetChat;
      return newChats;
    });
  };

  return (
    <main className="chat-container">
      <header className="chat-header glassmorphism">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {collapsed && (
            <button id="openSidebarBtn" className="icon-btn" title="展开侧边栏" onClick={() => setCollapsed(false)}>
              <PanelLeftOpen size={20} />
            </button>
          )}
          <h2>企业知识库 RAG 终端</h2>
        </div>
        <div className="status-indicator" id="wsStatus">
          <span className={`dot ${wsStatus === 'connected' ? 'connected' : 'disconnected'}`}></span> 
          {!isAuthenticated ? '请先登录' : (wsStatus === 'connected' ? '已连接至麓谷 AI 节点' : '连接断开')}
        </div>
      </header>

      <div className="chat-history" style={{ flex: 1, padding: 0, display: 'block', overflow: 'hidden' }}>
        {messages.length === 0 ? (
          <div style={{ padding: '32px', display: 'flex', flexDirection: 'column' }}>
            <div className="message system">
              <div className="avatar">🤖</div>
              <div className="content">
                <div>您好！我是拓维信息首席 AI 助理。已加载全量企业级文档，请问有什么可以帮您？</div>
                <div className="suggestion-chips">
                  <button className="suggestion-chip" disabled={!isAuthenticated} onClick={() => { if (!isAuthenticated) return onRequireAuth?.(); setInputText('帮我总结一下《大模型架构设计指南》的核心要点'); setTimeout(handleSend, 100); }}>💡 总结架构设计指南</button>
                  <button className="suggestion-chip" disabled={!isAuthenticated} onClick={() => { if (!isAuthenticated) return onRequireAuth?.(); setInputText('如何使用 RAG 架构实现内部知识库？'); setTimeout(handleSend, 100); }}>🏗️ RAG 知识库构建</button>
                  <button className="suggestion-chip" disabled={!isAuthenticated} onClick={() => { if (!isAuthenticated) return onRequireAuth?.(); setInputText('写一段 Python 脚本，演示大模型 Function Calling'); setTimeout(handleSend, 100); }}>💻 生成工具调用代码</button>
                  <button className="suggestion-chip" disabled={!isAuthenticated} onClick={() => { if (!isAuthenticated) return onRequireAuth?.(); setInputText('MCP 协议解决了什么痛点？'); setTimeout(handleSend, 100); }}>🔌 MCP 协议解析</button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            data={messages}
            style={{ flex: 1, height: '100%', width: '100%' }}
            itemContent={(index, msg) => (
              <div style={{ padding: '16px 32px', display: 'flex', flexDirection: 'column' }}>
                <Message 
                  message={msg} 
                  isStreamingLast={isStreaming && index === messages.length - 1} 
                  setArtifact={setArtifact}
                  messageIndex={index}
                  onEditSubmit={handleEditSubmit}
                  onBranchSwitch={handleBranchSwitch}
                  onHitlDecision={onHitlDecision}
                />
              </div>
            )}
            followOutput="smooth"
          />
        )}
      </div>

      <ChatInput 
        inputText={inputText}
        setInputText={setInputText}
        handleSend={handleSend}
        handleStop={handleStop}
        isStreaming={isStreaming}
        imageBase64={imageBase64}
        setImageBase64={setImageBase64}
        faceBase64={faceBase64}
        setFaceBase64={setFaceBase64}
        audioBase64={audioBase64}
        setAudioBase64={setAudioBase64}
        fileUpload={fileUpload}
        setFileUpload={setFileUpload}
        mode={mode}
        setMode={setMode}
        isAuthenticated={isAuthenticated}
        onRequireAuth={onRequireAuth}
      />
    </main>
  );
};

export default MainChat;
