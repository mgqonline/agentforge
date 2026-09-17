import { useState, useRef, useEffect } from 'react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  thoughts?: string[];
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const assistantMessage: Message = { role: 'assistant', content: '', thoughts: [] };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const apiBase = (window.location.port === '6000')
        ? `${window.location.protocol}//${window.location.hostname}:6001`
        : 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              break;
            }
            try {
              const data = JSON.parse(dataStr);
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                
                if (data.type === 'thought') {
                  lastMessage.thoughts = [...(lastMessage.thoughts || []), data.content];
                } else if (data.type === 'token') {
                  lastMessage.content += data.content;
                }
                
                return newMessages;
              });
            } catch (err) {
              console.error("Error parsing JSON:", err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Fetch error:", error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content = "网络错误，无法连接到大模型后端。";
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-container">
          <div className="logo-dot"></div>
          <h1>AI Agent Database Interface</h1>
        </div>
        <p>T3 Level End-to-End System</p>
      </header>

      <main className="chat-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>欢迎使用 MySQL 智能助手</h2>
            <p>基于 LangGraph 反思流构建，你可以直接问我关于数据库的问题。</p>
            <div className="suggestion-chips">
              <button onClick={() => setInput("查一下数据库里所有的表结构")}>查一下数据库里所有的表</button>
              <button onClick={() => setInput("统计一下今年一共有多少条订单？")}>统计今年的订单总量</button>
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? 'U' : 'AI'}
                </div>
                <div className="message-content">
                  {msg.thoughts && msg.thoughts.length > 0 && (
                    <div className="thought-process">
                      {msg.thoughts.map((t, i) => (
                        <div key={i} className="thought-step">{t}</div>
                      ))}
                    </div>
                  )}
                  {msg.content && <div className="final-answer">{msg.content}</div>}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      <footer className="input-container">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="告诉 Agent 你想要查询什么数据..."
            disabled={isLoading}
            className="chat-input"
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="send-button">
            {isLoading ? '...' : '发送'}
          </button>
        </form>
      </footer>
    </div>
  );
}

export default App;
