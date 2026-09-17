import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import Editor from '@monaco-editor/react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, ChevronRight, ChevronDown, Wrench, XCircle, CheckCircle2, Edit2, ChevronLeft, ArrowRight, Code, RefreshCw, FileText, FileAudio, ShieldAlert } from 'lucide-react';

const looksLikeCodeBlock = (text, lang = 'text') => {
  const normalizedLang = (lang || 'text').toLowerCase();
  const codeLangs = new Set([
    'js', 'javascript', 'jsx', 'ts', 'typescript', 'tsx', 'python', 'py', 'java',
    'go', 'rust', 'rs', 'c', 'cpp', 'csharp', 'cs', 'php', 'ruby', 'rb', 'swift',
    'kotlin', 'scala', 'sql', 'bash', 'sh', 'shell', 'zsh', 'powershell', 'ps1',
    'json', 'yaml', 'yml', 'toml', 'xml', 'html', 'css', 'scss', 'dockerfile'
  ]);
  if (codeLangs.has(normalizedLang)) return true;
  if (normalizedLang && !['text', 'txt', 'plain', 'plaintext', 'md', 'markdown'].includes(normalizedLang)) return true;

  const source = (text || '').trim();
  if (!source) return false;
  const codeSignals = [
    /(^|\n)\s*(class|def|function|const|let|var|import|export|return|if|for|while|try|catch|async|await)\b/,
    /(^|\n)\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b/i,
    /[{};]\s*($|\n)/,
    /=>|<\/?[a-z][\s\S]*?>/i,
    /^\s*[{[][\s\S]*[}\]]\s*$/,
    /\w+\([^)]*\)\s*[{:]?/
  ];
  return codeSignals.some(pattern => pattern.test(source));
};

const CodeBlock = ({ inline, className, children, setArtifact, isStreaming, ...props }) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const lang = match ? match[1] : 'text';
  const codeString = String(children).replace(/\n$/, '');

  // In react-markdown v10+, the 'inline' prop is no longer provided. 
  // We can infer it: if it lacks a language class AND has no newlines, it's likely inline code.
  const isInline = inline !== undefined ? inline : (!match && !String(children).includes('\n'));

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isInline) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  }

  const isReact = lang === 'jsx' || lang === 'tsx' || lang === 'react';
  const isCode = looksLikeCodeBlock(codeString, lang);

  if (!isCode) {
    return (
      <div className="plain-text-block">
        <pre>
          <code>{codeString}</code>
        </pre>
      </div>
    );
  }

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">{lang}</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          {isReact && setArtifact && (
            <button className="copy-btn" onClick={() => setArtifact({ isOpen: true, content: codeString, language: lang })}>
              ⚡ Open in Artifacts
            </button>
          )}
          {!isStreaming && (
            <button className="copy-btn" onClick={() => setIsEditing(!isEditing)}>
              {isEditing ? 'Done' : 'Edit'}
            </button>
          )}
          <button className={`copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy}>
            {copied ? <Check size={14} style={{ display: 'inline', marginRight: 4 }} /> : <Copy size={14} style={{ display: 'inline', marginRight: 4 }} />}
            {copied ? '已复制!' : '复制'}
          </button>
        </div>
      </div>
      <div style={{ width: '100%', background: '#1e1e1e', overflow: 'hidden' }}>
        {isEditing ? (
          <div style={{ height: '300px', padding: '10px 0' }}>
            <Editor
              height="100%"
              language={lang === 'text' ? 'plaintext' : lang}
              theme="vs-dark"
              value={codeString}
              options={{
                readOnly: !isEditing || isStreaming,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                fontSize: 14,
              }}
            />
          </div>
        ) : (
          <div style={{ margin: 0, fontSize: '14px' }}>
            <SyntaxHighlighter
              language={lang === 'text' ? 'text' : lang}
              style={vscDarkPlus}
              customStyle={{ margin: 0, padding: '16px', background: 'transparent' }}
              wrapLongLines={true}
            >
              {codeString}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
};

const ThoughtsBlock = ({ thoughts, isStreaming }) => {
  const [open, setOpen] = useState(true);

  if (!thoughts || thoughts.length === 0) return null;

  return (
    <div className="thought-process" style={{ padding: 0 }}>
      <summary onClick={() => setOpen(!open)} style={{ listStyle: 'none' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          ✨ 思考过程 & 工具调用 ({thoughts.length} 步)
        </div>
      </summary>
      {open && (
        <ul className={!isStreaming ? 'completed' : ''}>
          {thoughts.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

const ToolCallBlock = ({ toolCall, completed }) => {
  let argsFormatted = toolCall.args;
  try {
    const parsedArgs = typeof toolCall.args === 'string' ? JSON.parse(toolCall.args) : toolCall.args;
    argsFormatted = JSON.stringify(parsedArgs, null, 2);
  } catch (e) {}

  return (
    <div className="tool-execution-block">
      <div className="tool-header">
        <Wrench size={14} />
        <span className="tool-name">Calling: {toolCall.name}</span>
        <span className={`tool-status ${completed ? 'success' : 'running'}`}>
          {completed ? 'Completed' : 'Executing...'}
        </span>
      </div>
      <div className="tool-args">
        <pre><code>{argsFormatted}</code></pre>
      </div>
    </div>
  );
};

const CitationsBlock = ({ citations }) => {
  if (!citations || citations.length === 0) return null;
  
  return (
    <div className="citations-container">
      {citations.map((src, i) => (
        <span key={i} className="citation-badge" title={src}>
          <CheckCircle2 size={14} />
          {src}
        </span>
      ))}
    </div>
  );
};

const HitlRequestBlock = ({ request, requestIndex, messageIndex, onHitlDecision }) => {
  const isPending = request.status === 'pending';
  const isSideEffect = request.params?.approval_kind === 'side_effect';
  const approveLabel = isSideEffect ? '确认继续分析' : '确认继续';
  const warning = isSideEffect
    ? '该请求包含副作用操作。当前只允许继续做风险分析，不授权写库、删除、发送或外部调用。'
    : (request.params?.warning || '该操作需要人工确认后才能继续。');

  return (
    <div className="hitl-request-block">
      <div className="hitl-header">
        <ShieldAlert size={16} />
        <span>高风险操作审批</span>
        <span className={`hitl-status ${request.status || 'pending'}`}>
          {isPending ? '等待确认' : request.status === 'approved' ? '已批准' : '已拒绝'}
        </span>
      </div>
      <div className="hitl-warning">{warning}</div>
      <pre className="hitl-task">{request.content}</pre>
      {isPending && (
        <div className="hitl-actions">
          <button className="hitl-btn reject" onClick={() => onHitlDecision(messageIndex, requestIndex, false)}>拒绝</button>
          <button className="hitl-btn approve" onClick={() => onHitlDecision(messageIndex, requestIndex, true)}>{approveLabel}</button>
        </div>
      )}
    </div>
  );
};

const Message = ({ message, isStreamingLast, setArtifact, messageIndex, onEditSubmit, onBranchSwitch, onHitlDecision }) => {
  const isSystem = message.role === 'system' || message.role === 'assistant';
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  const markdownComponents = React.useMemo(() => ({
    code: (props) => <CodeBlock {...props} setArtifact={setArtifact} isStreaming={isStreamingLast} />,
    p: ({node, ...props}) => <div className="p-block" style={{ marginBottom: '12px' }} {...props} />,
    pre: ({node, ...props}) => <div className="pre-block" {...props} />
  }), [setArtifact, isStreamingLast]);

  // Extract citations
  let processedContent = message.content || '';
  let citations = [...(message.citations || [])];
  
  const citationRegex = /\[source:\s*(.*?)\]/gi;
  let match;
  while ((match = citationRegex.exec(message.content)) !== null) {
    if (!citations.includes(match[1])) {
      citations.push(match[1]);
    }
  }
  processedContent = processedContent.replace(citationRegex, '').trim();

  return (
    <div className={`message ${isSystem ? 'system' : 'user'}`}>
      <div className="avatar">{isSystem ? '🤖' : '👤'}</div>
      <div className="content" style={{ width: '100%', minWidth: 0 }}>
        {message.imageBase64 && (
          <img src={message.imageBase64} style={{ maxWidth: '200px', borderRadius: '8px', display: 'block', marginBottom: '8px' }} alt="uploaded" />
        )}
        
        {message.faceBase64 && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(255,140,0,0.2)', border: '1px solid rgba(255,165,0,0.5)', padding: '4px 10px', borderRadius: '20px', marginBottom: '8px', color: '#ffa500', fontSize: '12px', fontWeight: 600 }}>
            <span>👤 专项人脸核真照片</span>
            <img src={message.faceBase64} style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }} alt="face verify" />
          </div>
        )}
        
        {message.fileUpload && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'var(--bg-glass)', border: '1px solid var(--glass-border)', padding: '8px 12px', borderRadius: '8px', marginBottom: '8px' }}>
            {message.fileUpload.type?.includes('audio') || /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(message.fileUpload.name) ? (
              <FileAudio size={16} style={{ color: '#52c41a' }} />
            ) : (
              <FileText size={16} style={{ color: 'var(--accent-blue)' }} />
            )}
            <span style={{ fontSize: '13px', fontWeight: 500 }}>{message.fileUpload.name}</span>
          </div>
        )}
        
        {isSystem && <ThoughtsBlock thoughts={message.thoughts} isStreaming={isStreamingLast} />}
        
        {isSystem && message.toolCalls && message.toolCalls.map((tc, i) => (
          <ToolCallBlock key={i} toolCall={tc} completed={tc.completed} />
        ))}

        {isSystem && message.hitlRequests && message.hitlRequests.map((request, i) => (
          <HitlRequestBlock
            key={i}
            request={request}
            requestIndex={i}
            messageIndex={messageIndex}
            onHitlDecision={onHitlDecision}
          />
        ))}

        {isSystem ? (
          <div className="text-content markdown-body">
            <ReactMarkdown components={markdownComponents}>
              {processedContent}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="user-message-content" style={{ position: 'relative' }}>
            {isEditing ? (
              <div className="edit-container" style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                <textarea 
                  value={editContent} 
                  onChange={(e) => setEditContent(e.target.value)}
                  style={{ width: '100%', minHeight: '80px', padding: '12px', borderRadius: '8px', border: '1px solid var(--glass-border)', background: 'var(--bg-glass)', color: 'var(--text-primary)', resize: 'vertical' }}
                />
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button onClick={() => setIsEditing(false)} style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: 'transparent', cursor: 'pointer' }}>取消</button>
                  <button onClick={() => { setIsEditing(false); onEditSubmit(messageIndex, editContent); }} style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: 'var(--accent-blue)', color: 'white', cursor: 'pointer' }}>发送 & 分支</button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div style={{ whiteSpace: 'pre-wrap' }}>{processedContent}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button className="icon-btn edit-btn" onClick={() => { setEditContent(message.content); setIsEditing(true); }} style={{ opacity: 0.5 }} title="编辑并分支">
                    <Edit2 size={16} />
                  </button>
                  <button className="icon-btn retry-btn" onClick={() => onEditSubmit(messageIndex, message.content)} style={{ opacity: 0.5 }} title="重新发送此问题">
                    <RefreshCw size={16} />
                  </button>
                </div>
              </div>
            )}
            
            {!isEditing && message.branches && message.branches.length > 1 && (
              <div className="branch-controls" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <button 
                  onClick={() => onBranchSwitch(messageIndex, -1)} 
                  disabled={message.currentBranch === 0}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', opacity: message.currentBranch === 0 ? 0.3 : 1 }}
                >
                  <ChevronLeft size={14} />
                </button>
                <span>{message.currentBranch + 1} / {message.branches.length}</span>
                <button 
                  onClick={() => onBranchSwitch(messageIndex, 1)} 
                  disabled={message.currentBranch === message.branches.length - 1}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', opacity: message.currentBranch === message.branches.length - 1 ? 0.3 : 1 }}
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            )}
          </div>
        )}

        {isSystem && <CitationsBlock citations={citations} />}

        {isSystem && message.followUps && (
          <div className="suggestion-chips">
            {message.followUps.map((suggestion, i) => (
              <button key={i} className="suggestion-chip" onClick={() => window.fillAndSend && window.fillAndSend(suggestion)}>
                ✨ {suggestion}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;
