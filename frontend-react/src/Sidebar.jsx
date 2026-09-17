import React from 'react';
import { PanelLeftClose, Plus, MessageSquare, Trash2 } from 'lucide-react';

const Sidebar = ({ collapsed, setCollapsed, chats, currentChatId, switchChat, createNewChat, deleteChat, accountControl }) => {
  return (
    <aside className={`sidebar glassmorphism ${collapsed ? 'collapsed' : ''}`} id="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon"></div>
          <h1>Talkweb Agent</h1>
        </div>
        <button id="closeSidebarBtn" className="icon-btn" title="收起侧边栏" onClick={() => setCollapsed(true)}>
          <PanelLeftClose size={20} />
        </button>
      </div>
      
      <div className="sidebar-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: '8px' }}>
        <span>历史对话</span>
        <button id="newChatBtn" className="new-chat-btn" title="新建对话" onClick={createNewChat}>
          <Plus size={16} />
        </button>
      </div>
      
      <ul className="history-list" id="historyList">
        {chats.map(chat => (
          <li 
            key={chat.id} 
            className={`history-item ${chat.id === currentChatId ? 'active' : ''}`}
            onClick={() => switchChat(chat.id)}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}
          >
            <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {chat.title || '新对话'}
            </span>
            <button 
              className="delete-chat-btn" 
              onClick={(e) => deleteChat(e, chat.id)}
              title="删除此对话"
            >
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>

      <div className="sidebar-account-zone">
        {accountControl}
      </div>
    </aside>
  );
};

export default Sidebar;
