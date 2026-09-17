// DOM Elements
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const modeSwitch = document.getElementById('modeSwitch');
const wsStatus = document.getElementById('wsStatus');

const loadingStatus = document.getElementById('loadingStatus');
const loadingText = loadingStatus.querySelector('span');

const uploadImageBtn = document.getElementById('uploadImageBtn');
const imageInput = document.getElementById('imageInput');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imagePreview = document.getElementById('imagePreview');
const removeImageBtn = document.getElementById('removeImageBtn');

const recordAudioBtn = document.getElementById('recordAudioBtn');
const audioInput = document.getElementById('audioInput');
const audioPreviewContainer = document.getElementById('audioPreviewContainer');
const removeAudioBtn = document.getElementById('removeAudioBtn');

const filePreviewContainer = document.getElementById('filePreviewContainer');
const filePreviewIcon = document.getElementById('filePreviewIcon');
const filePreviewName = document.getElementById('filePreviewName');
const removeFileBtn = document.getElementById('removeFileBtn');

const uploadFaceBtn = document.getElementById('uploadFaceBtn');
const faceInput = document.getElementById('faceInput');
const facePreviewContainer = document.getElementById('facePreviewContainer');
const facePreview = document.getElementById('facePreview');
const removeFaceBtn = document.getElementById('removeFaceBtn');

const historyList = document.getElementById('historyList');
const newChatBtn = document.getElementById('newChatBtn');

let ws = null;
let currentAssistantMessageDiv = null;
let currentAssistantContent = null;
let currentThoughtProcess = null;
let isStreaming = false;
let currentImageBase64 = null;
let currentFaceBase64 = null;
let currentAudioBase64 = null;
let currentFileUpload = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let authUser = null;
let authToken = localStorage.getItem('talkweb_auth_token') || '';

// Chat History State
let chats = [];
let currentChatId = null;

function getStorageScope(userId) {
  const port = window.location.port || 'default';
  return `talkweb:${window.location.hostname}:${port}:${userId || (authUser && authUser.user_id) || 'guest'}`;
}

function storageKey(name, userId) {
  return `${getStorageScope(userId)}:${name}`;
}

function getUserId() {
  return (authUser && authUser.user_id) || localStorage.getItem('talkweb_user_id') || getSessionId();
}

function getSessionId() {
  const key = storageKey('session_id');
  const saved = localStorage.getItem(key);
  if (saved) return saved;
  const generated = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  localStorage.setItem(key, generated);
  return generated;
}

function getBackendUrl(path = '') {
  const normPath = path.startsWith('/') ? path : `/${path}`;
  if (import.meta.env?.VITE_API_BASE_URL) {
    return `${import.meta.env.VITE_API_BASE_URL}${normPath}`;
  }
  if (['6000', '6002'].includes(window.location.port)) {
    return `${window.location.protocol}//${window.location.hostname}:6001${normPath}`;
  }
  return `http://localhost:8000${normPath}`;
}

function getWsUrl(path = '') {
  const normPath = path.startsWith('/') ? path : `/${path}`;
  if (import.meta.env?.VITE_WS_BASE_URL) {
    return `${import.meta.env.VITE_WS_BASE_URL}${normPath}`;
  }
  if (['6000', '6002'].includes(window.location.port)) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.hostname}:6001${normPath}`;
  }
  return `ws://localhost:8000${normPath}`;
}

function authHeaders() {
  return {
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    'X-Session-Id': getSessionId(),
    'X-User-Id': getUserId()
  };
}

async function createWsTicket(sessionId) {
  const response = await fetch(getBackendUrl('/api/agent/ws-ticket'), {
    method: 'POST',
    headers: {
      ...authHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ session_id: sessionId })
  });
  if (!response.ok) {
    throw new Error(`ws ticket rejected: ${response.status}`);
  }
  return response.json();
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function scrollToBottom() {
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Extract citations like [source: filename]
function processContentAndCitations(content) {
  const citationRegex = /\[source:\s*(.*?)\]/gi;
  let citations = [];
  let match;
  let processedContent = content;
  
  while ((match = citationRegex.exec(content)) !== null) {
    if (!citations.includes(match[1])) {
      citations.push(match[1]);
    }
  }
  
  processedContent = processedContent.replace(citationRegex, '').trim();
  
  return { processedContent, citations };
}

window.copyCode = function(btn) {
  const pre = btn.closest('.code-block');
  const code = pre.querySelector('code').innerText;
  navigator.clipboard.writeText(code).then(() => {
    const originalText = btn.innerText;
    btn.innerText = '已复制!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerText = originalText;
      btn.classList.remove('copied');
    }, 2000);
  });
};

function looksLikeCodeBlock(text, lang = 'text') {
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
}

function addCopyButtons(container) {
  container.querySelectorAll('pre').forEach(pre => {
    if (!pre.parentNode.classList.contains('code-block') && !pre.parentNode.classList.contains('plain-text-block')) {
      const wrapper = document.createElement('div');
      const codeElement = pre.querySelector('code');
      let lang = 'text';
      if (codeElement && codeElement.className) {
        const match = codeElement.className.match(/language-(\w+)/);
        if (match) lang = match[1];
      }
      const content = codeElement ? codeElement.innerText : pre.innerText;
      const isCode = looksLikeCodeBlock(content, lang);

      wrapper.className = isCode ? 'code-block' : 'plain-text-block';
      pre.parentNode.insertBefore(wrapper, pre);

      if (isCode) {
        const header = document.createElement('div');
        header.className = 'code-header';
        header.innerHTML = `<span class="code-lang">${lang}</span><button class="copy-btn" onclick="copyCode(this)">复制</button>`;
        wrapper.appendChild(header);
      }
      wrapper.appendChild(pre);
    }
  });
}

function updateLiveCitationsUI(messageDiv, citations) {
  if (!citations || citations.length === 0) return;
  
  const contentDiv = messageDiv.querySelector('.content');
  let citationsDiv = messageDiv.querySelector('.citations-container');
  
  if (!citationsDiv) {
    citationsDiv = document.createElement('div');
    citationsDiv.className = 'citations-container';
    const textContent = messageDiv.querySelector('.text-content');
    if (textContent) {
      contentDiv.insertBefore(citationsDiv, textContent.nextSibling);
    } else {
      contentDiv.appendChild(citationsDiv);
    }
  }
  
  citationsDiv.innerHTML = citations.map(src => 
    `<span class="citation-badge" title="${escapeHtml(src)}">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"></path></svg>
      ${escapeHtml(src)}
    </span>`
  ).join('');
}

// ---- Local Storage Management ----
function loadChats() {
  const saved = localStorage.getItem(storageKey('chats'));
  if (saved) {
    chats = JSON.parse(saved);
  }
  if (chats.length === 0) {
    createNewChat();
  } else {
    // 默认新开一个会话，除非上一个会话也是空的
    if (chats[0].messages.length === 0) {
      switchChat(chats[0].id);
    } else {
      createNewChat();
    }
  }
  renderSidebar();
}

function saveChats() {
  try {
    localStorage.setItem(storageKey('chats'), JSON.stringify(chats));
  } catch (err) {
    console.warn('本地存储容量超限或异常:', err);
  }
  renderSidebar();
}

function createNewChat() {
  const newChat = {
    id: Date.now().toString(),
    title: '新对话',
    messages: []
  };
  chats.unshift(newChat);
  switchChat(newChat.id);
  saveChats();
}

function switchChat(chatId) {
  currentChatId = chatId;
  const chat = chats.find(c => c.id === chatId);
  renderMessages(chat.messages);
  renderSidebar();
}

function renderSidebar() {
  historyList.innerHTML = '';
  chats.forEach(chat => {
    const li = document.createElement('li');
    li.className = 'history-item';
    if (chat.id === currentChatId) li.classList.add('active');
    
    li.style.display = 'flex';
    li.style.justifyContent = 'space-between';
    li.style.alignItems = 'center';
    li.style.gap = '8px';
    
    const textSpan = document.createElement('span');
    textSpan.style.flex = '1';
    textSpan.style.whiteSpace = 'nowrap';
    textSpan.style.overflow = 'hidden';
    textSpan.style.textOverflow = 'ellipsis';
    textSpan.textContent = chat.title || '新对话';
    
    const delBtn = document.createElement('button');
    delBtn.className = 'delete-chat-btn';
    delBtn.title = '删除此对话';
    delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>';
    delBtn.onclick = (e) => {
      e.stopPropagation();
      deleteChat(chat.id);
    };
    
    li.appendChild(textSpan);
    li.appendChild(delBtn);
    li.onclick = () => switchChat(chat.id);
    historyList.appendChild(li);
  });
}

function deleteChat(chatId) {
  if (isStreaming) return;
  chats = chats.filter(c => c.id !== chatId);
  if (chats.length === 0) {
    createNewChat();
  } else {
    if (chatId === currentChatId) {
      switchChat(chats[0].id);
    } else {
      saveChats();
    }
  }
}

function renderMessages(messages) {
  chatHistory.innerHTML = '';
  if (messages.length === 0) {
    chatHistory.innerHTML = `
      <div class="message system">
        <div class="avatar">🤖</div>
        <div class="content">
          <div>您好！我是拓维信息首席 AI 助理。已加载全量企业级文档，请问有什么可以帮您？</div>
          <div class="suggestion-chips">
            <button class="suggestion-chip" onclick="fillAndSend('帮我总结一下《大模型架构设计指南》的核心要点')">💡 总结架构设计指南</button>
            <button class="suggestion-chip" onclick="fillAndSend('如何使用 RAG 架构实现内部知识库？')">🏗️ RAG 知识库构建</button>
            <button class="suggestion-chip" onclick="fillAndSend('写一段 Python 脚本，演示大模型 Function Calling')">💻 生成工具调用代码</button>
            <button class="suggestion-chip" onclick="fillAndSend('MCP 协议解决了什么痛点？')">🔌 MCP 协议解析</button>
          </div>
        </div>
      </div>
    `;
    return;
  }
  
  messages.forEach(msg => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${msg.role}`;
    
    let imgHtml = '';
    if (msg.imageBase64) {
      imgHtml = `<img src="${msg.imageBase64}" style="max-width:200px; border-radius:8px; display:block; margin-bottom:8px;">`;
    }
    
    let fileHtml = '';
    if (msg.fileUpload) {
      const isAudio = (msg.fileUpload.type && msg.fileUpload.type.includes('audio')) || /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(msg.fileUpload.name);
      const iconSvg = isAudio ? 
        `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:#52c41a"><path d="M4 6.835V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-.343"></path><path d="M14 2v5a1 1 0 0 0 1 1h5"></path><path d="M2 19a2 2 0 0 1 4 0v1a2 2 0 0 1-4 0v-4a6 6 0 0 1 12 0v4a2 2 0 0 1-4 0v-1a2 2 0 0 1 4 0"></path></svg>` : 
        `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent-blue)"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`;
      const bgStyle = isAudio ? 'background:rgba(82,196,26,0.2);' : 'background:var(--bg-glass);';
      fileHtml = `<div style="display:inline-flex;align-items:center;gap:8px;${bgStyle}border:1px solid var(--glass-border);padding:8px 12px;border-radius:8px;margin-bottom:8px;font-size:13px;font-weight:500;">${iconSvg}${msg.fileUpload.name}</div>`;
    }

    let faceHtml = '';
    if (msg.faceBase64) {
      faceHtml = `<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,140,0,0.2);border:1px solid rgba(255,165,0,0.5);padding:4px 10px;border-radius:20px;margin-bottom:8px;color:#ffa500;font-size:12px;font-weight:600;"><span>👤 专项人脸识别质验图</span><img src="${msg.faceBase64}" style="width:24px;height:24px;border-radius:50%;object-fit:cover;"></div>`;
    }
    
    if (msg.role === 'user') {
      msgDiv.innerHTML = `<div class="avatar">👤</div><div class="content">${imgHtml}${faceHtml}${fileHtml}${escapeHtml(msg.content)}</div>`;
    } else {
      let thoughtsHtml = '';
      if (msg.thoughts && msg.thoughts.length > 0) {
        thoughtsHtml = `
          <details class="thought-process">
            <summary>✨ 思考过程 & 工具调用 (${msg.thoughts.length} 步)</summary>
            <ul>${msg.thoughts.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>
          </details>
        `;
      }
      
      const { processedContent, citations } = processContentAndCitations(msg.content);
      let allCitations = [...(msg.citations || [])];
      citations.forEach(c => {
        if (!allCitations.includes(c)) allCitations.push(c);
      });
      
      msgDiv.innerHTML = `<div class="avatar">🤖</div><div class="content">${thoughtsHtml}<div class="text-content markdown-body">${marked.parse(processedContent)}</div></div>`;
      addCopyButtons(msgDiv);
      updateLiveCitationsUI(msgDiv, allCitations);
    }
    chatHistory.appendChild(msgDiv);
  });
  scrollToBottom();
}

userInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  if (this.scrollHeight >= 200) {
    this.style.overflowY = 'auto';
  } else {
    this.style.overflowY = 'hidden';
  }
  if(this.value === '') {
    this.style.height = 'auto';
    this.style.overflowY = 'hidden';
  }
});

// File & Image Upload Logic
function handleFileSelection(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  if (file.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const MAX_SIZE = 1600;
        let width = img.width;
        let height = img.height;
        
        if (width > height && width > MAX_SIZE) {
          height *= MAX_SIZE / width;
          width = MAX_SIZE;
        } else if (height > MAX_SIZE) {
          width *= MAX_SIZE / height;
          height = MAX_SIZE;
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        
        currentImageBase64 = canvas.toDataURL('image/jpeg', 0.8);
        currentFileUpload = null;
        currentAudioBase64 = null;
        currentFaceBase64 = null;
        filePreviewContainer.classList.add('hidden');
        if (audioPreviewContainer) audioPreviewContainer.classList.add('hidden');
        if (facePreviewContainer) facePreviewContainer.classList.add('hidden');
        imagePreview.src = currentImageBase64;
        imagePreviewContainer.classList.remove('hidden');
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  } else {
    const reader = new FileReader();
    reader.onload = (event) => {
      let fileType = file.type;
      if (!fileType && /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(file.name)) {
        fileType = 'audio/mpeg';
      }
      currentFileUpload = {
        name: file.name,
        type: fileType,
        data: event.target.result
      };
      currentImageBase64 = null;
      currentAudioBase64 = null;
      currentFaceBase64 = null;
      imagePreviewContainer.classList.add('hidden');
      if (audioPreviewContainer) audioPreviewContainer.classList.add('hidden');
      if (facePreviewContainer) facePreviewContainer.classList.add('hidden');
      filePreviewName.textContent = file.name;
      const isAudio = (fileType && fileType.includes('audio')) || /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(file.name);
      if (filePreviewIcon) filePreviewIcon.textContent = isAudio ? '🎵' : '📄';
      filePreviewContainer.style.background = isAudio ? 'rgba(82, 196, 26, 0.2)' : 'rgba(100,150,250,0.2)';
      filePreviewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }
  e.target.value = '';
}

uploadImageBtn.addEventListener('click', () => {
  imageInput.click();
});
imageInput.addEventListener('change', handleFileSelection);

removeImageBtn.addEventListener('click', () => {
  currentImageBase64 = null;
  imageInput.value = '';
  imagePreviewContainer.classList.add('hidden');
});

if (uploadFaceBtn && faceInput) {
  uploadFaceBtn.addEventListener('click', () => faceInput.click());
  faceInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        currentFaceBase64 = ev.target.result;
        currentImageBase64 = null;
        currentFileUpload = null;
        currentAudioBase64 = null;
        if (imagePreviewContainer) imagePreviewContainer.classList.add('hidden');
        if (filePreviewContainer) filePreviewContainer.classList.add('hidden');
        if (audioPreviewContainer) audioPreviewContainer.classList.add('hidden');
        if (facePreview) facePreview.src = currentFaceBase64;
        if (facePreviewContainer) facePreviewContainer.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    }
    e.target.value = '';
  });
}

if (removeFaceBtn) {
  removeFaceBtn.addEventListener('click', () => {
    currentFaceBase64 = null;
    if (faceInput) faceInput.value = '';
    if (facePreviewContainer) facePreviewContainer.classList.add('hidden');
  });
}

// Audio File Upload Logic (replacing live recording)
recordAudioBtn.addEventListener('click', () => {
  if (audioInput) audioInput.click();
});
if (audioInput) {
  audioInput.addEventListener('change', handleFileSelection);
}

if (removeAudioBtn) {
  removeAudioBtn.addEventListener('click', () => {
    currentAudioBase64 = null;
    if (audioPreviewContainer) audioPreviewContainer.classList.add('hidden');
  });
}

removeFileBtn.addEventListener('click', () => {
  currentFileUpload = null;
  imageInput.value = '';
  if (audioInput) audioInput.value = '';
  filePreviewContainer.classList.add('hidden');
});

// Sidebar Events
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const openSidebarBtn = document.getElementById('openSidebarBtn');
const sidebar = document.getElementById('sidebar');

if (closeSidebarBtn && openSidebarBtn && sidebar) {
  closeSidebarBtn.addEventListener('click', () => {
    sidebar.classList.add('collapsed');
    openSidebarBtn.classList.remove('hidden');
  });
  
  openSidebarBtn.addEventListener('click', () => {
    sidebar.classList.remove('collapsed');
    openSidebarBtn.classList.add('hidden');
  });
}

newChatBtn.addEventListener('click', () => {
  if (isStreaming) return;
  createNewChat();
});

async function connectWebSocket() {
  if (!authToken || !authUser) {
    wsStatus.innerHTML = '<span class="dot disconnected"></span> 请先登录';
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
    return;
  }
  const sessionId = getSessionId();
  const userId = getUserId();
  let ticketPayload;
  try {
    ticketPayload = await createWsTicket(sessionId);
  } catch (error) {
    console.error('WebSocket ticket failed:', error);
    wsStatus.innerHTML = '<span class="dot disconnected"></span> 连接鉴权失败 (正在重试...)';
    if (authToken && authUser) setTimeout(connectWebSocket, 3000);
    return;
  }

  const qs = new URLSearchParams({ session_id: sessionId, user_id: userId, ticket: ticketPayload.ticket });
  ws = new WebSocket(getWsUrl(`/ws/chat?${qs.toString()}`));

  ws.onopen = () => {
    wsStatus.innerHTML = '<span class="dot connected"></span> 已连接至麓谷 AI 节点';
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'status') {
      // Create thought process UI dynamically if not exists
      if (!currentAssistantMessageDiv) {
        currentAssistantMessageDiv = document.createElement('div');
        currentAssistantMessageDiv.className = 'message system';
        currentAssistantMessageDiv.innerHTML = `
          <div class="avatar">🤖</div>
          <div class="content">
            <details class="thought-process" open>
              <summary>✨ 思考过程 & 工具调用</summary>
              <ul></ul>
            </details>
            <div class="text-content markdown-body"></div>
          </div>
        `;
        chatHistory.appendChild(currentAssistantMessageDiv);
        currentThoughtProcess = currentAssistantMessageDiv.querySelector('.thought-process ul');
        currentAssistantContent = currentAssistantMessageDiv.querySelector('.text-content');
        
        // Push empty bot message to state to store thoughts
        const chat = chats.find(c => c.id === currentChatId);
        chat.messages.push({ role: 'system', content: '', thoughts: [], citations: [] });
      }
      
      const li = document.createElement('li');
      li.textContent = data.content;
      currentThoughtProcess.appendChild(li);
      
      const chat = chats.find(c => c.id === currentChatId);
      const lastMsg = chat.messages[chat.messages.length - 1];
      if(!lastMsg.thoughts) lastMsg.thoughts = [];
      lastMsg.thoughts.push(data.content);
      
      scrollToBottom();
    } 
    else if (data.type === 'tool_call') {
      if (!currentAssistantMessageDiv) {
        currentAssistantMessageDiv = document.createElement('div');
        currentAssistantMessageDiv.className = 'message system';
        currentAssistantMessageDiv.innerHTML = `
          <div class="avatar">🤖</div>
          <div class="content"><div class="text-content markdown-body"></div></div>
        `;
        chatHistory.appendChild(currentAssistantMessageDiv);
        currentAssistantContent = currentAssistantMessageDiv.querySelector('.text-content');
        
        const chat = chats.find(c => c.id === currentChatId);
        chat.messages.push({ role: 'system', content: '', thoughts: [] });
      }
      
      const contentDiv = currentAssistantMessageDiv.querySelector('.content');
      const toolDiv = document.createElement('div');
      toolDiv.className = 'tool-execution-block';
      toolDiv.dataset.toolName = data.name;
      
      let argsFormatted = data.args;
      try {
        const parsedArgs = typeof data.args === 'string' ? JSON.parse(data.args) : data.args;
        argsFormatted = JSON.stringify(parsedArgs, null, 2);
      } catch (e) {}

      toolDiv.innerHTML = `
        <div class="tool-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 9.36l-7.1 7.1a1 1 0 0 1-1.41-1.41l7.1-7.1a6 6 0 0 1 9.36-7.94l-3.77 3.77a1 1 0 0 0 0 1.4z"></path></svg>
          <span class="tool-name">Calling: ${escapeHtml(data.name)}</span>
          <span class="tool-status running">Executing...</span>
        </div>
        <div class="tool-args">
          <pre><code>${escapeHtml(argsFormatted)}</code></pre>
        </div>
      `;
      
      const textContent = currentAssistantMessageDiv.querySelector('.text-content');
      if (textContent) {
        contentDiv.insertBefore(toolDiv, textContent);
      } else {
        contentDiv.appendChild(toolDiv);
      }
      scrollToBottom();
    }
    else if (data.type === 'tool_call_result') {
      if (currentAssistantMessageDiv) {
        const toolBlocks = currentAssistantMessageDiv.querySelectorAll('.tool-execution-block');
        for (let block of toolBlocks) {
          if (block.dataset.toolName === data.name) {
            const statusSpan = block.querySelector('.tool-status');
            if (statusSpan) {
              statusSpan.className = 'tool-status success';
              statusSpan.textContent = 'Completed';
            }
          }
        }
      }
    }
    else if (data.type === 'citations') {
      if (currentAssistantMessageDiv) {
        const chat = chats.find(c => c.id === currentChatId);
        let allCitations = chat.messages[chat.messages.length - 1].citations || [];
        data.content.forEach(c => {
          if (!allCitations.includes(c)) allCitations.push(c);
        });
        chat.messages[chat.messages.length - 1].citations = allCitations;
        
        updateLiveCitationsUI(currentAssistantMessageDiv, allCitations);
        scrollToBottom();
      }
    }
    else if (data.type === 'stream_start') {
      isStreaming = true;
      document.getElementById('stopBtn').classList.remove('hidden');
      document.getElementById('sendBtn').classList.add('hidden');
      
      loadingStatus.classList.add('hidden');
      if (!currentAssistantMessageDiv) {
        currentAssistantMessageDiv = document.createElement('div');
        currentAssistantMessageDiv.className = 'message system';
        currentAssistantMessageDiv.innerHTML = `
          <div class="avatar">🤖</div>
          <div class="content"><div class="text-content markdown-body"></div></div>
        `;
        chatHistory.appendChild(currentAssistantMessageDiv);
        currentAssistantContent = currentAssistantMessageDiv.querySelector('.text-content');
        
        const chat = chats.find(c => c.id === currentChatId);
        chat.messages.push({ role: 'system', content: '', thoughts: [] });
      }
      
      // Close thought process when streaming starts
      const details = currentAssistantMessageDiv.querySelector('details');
      if (details) details.removeAttribute('open');
      
      scrollToBottom();
    }
    else if (data.type === 'stream_chunk') {
      if (currentAssistantContent) {
        // Save to state
        const chat = chats.find(c => c.id === currentChatId);
        chat.messages[chat.messages.length - 1].content += data.content;
        
        if (!window.isRenderingStream) {
          window.isRenderingStream = true;
          // Use requestAnimationFrame to batch render updates
          requestAnimationFrame(() => {
            const currentMsg = chat.messages[chat.messages.length - 1];
            const { processedContent, citations } = processContentAndCitations(currentMsg.content);
            
            // Update state citations
            let allCitations = currentMsg.citations || [];
            citations.forEach(c => {
              if (!allCitations.includes(c)) allCitations.push(c);
            });
            currentMsg.citations = allCitations;
            
            // Render Markdown
            currentAssistantContent.innerHTML = marked.parse(processedContent);
            addCopyButtons(currentAssistantContent);
            updateLiveCitationsUI(currentAssistantMessageDiv, allCitations);
            scrollToBottom();
            
            // Throttle rendering (around ~30fps max) to prevent UI freeze on huge payloads
            setTimeout(() => {
              window.isRenderingStream = false;
            }, 30);
          });
        }

        // Auto update chat title based on first message
        if (chat.title === '新对话' && chat.messages.length >= 2) {
          chat.title = chat.messages[0].content.replace(/\s+/g, ' ').substring(0, 15) + '...';
          saveChats();
          renderSidebar();
        }
      }
    }
    else if (data.type === 'follow_ups') {
      if (currentAssistantMessageDiv) {
        const contentDiv = currentAssistantMessageDiv.querySelector('.content');
        const chipsDiv = document.createElement('div');
        chipsDiv.className = 'suggestion-chips';
        
        data.content.forEach(suggestion => {
          const btn = document.createElement('button');
          btn.className = 'suggestion-chip';
          btn.innerHTML = `✨ ${escapeHtml(suggestion)}`;
          btn.onclick = () => fillAndSend(suggestion);
          chipsDiv.appendChild(btn);
        });
        
        contentDiv.appendChild(chipsDiv);
        scrollToBottom();
      }
    }
    else if (data.type === 'stream_end') {
      isStreaming = false;
      document.getElementById('stopBtn').classList.add('hidden');
      document.getElementById('sendBtn').classList.remove('hidden');
      
      // Force final flush in case the last chunk was caught in the throttle buffer
      if (currentAssistantContent) {
        const chat = chats.find(c => c.id === currentChatId);
        const currentMsg = chat.messages[chat.messages.length - 1];
        const { processedContent, citations } = processContentAndCitations(currentMsg.content);
        currentAssistantContent.innerHTML = marked.parse(processedContent);
        addCopyButtons(currentAssistantContent);
        updateLiveCitationsUI(currentAssistantMessageDiv, currentMsg.citations || []);
        scrollToBottom();
      }
      
      if (currentThoughtProcess) {
        currentThoughtProcess.classList.add('completed');
      }
      currentAssistantMessageDiv = null;
      currentAssistantContent = null;
      currentThoughtProcess = null;
      saveChats();
    }
    else if (data.type === 'task_started') {
      ws.currentTaskId = data.task_id;
    }
    else if (data.type === 'task_complete') {
      if (ws.currentTaskId === data.task_id) {
        ws.currentTaskId = null;
      }
    }
  };

  ws.onclose = () => {
    wsStatus.innerHTML = '<span class="dot disconnected"></span> 连接断开 (正在重连...)';
    if (authToken && authUser) setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (error) => {
    console.error('WebSocket Error:', error);
  };
}

// Helper to fill input and auto-send from chips
window.fillAndSend = function(text) {
  if (!authUser) {
    const accountTrigger = document.querySelector('.account-trigger');
    if (accountTrigger) accountTrigger.click();
    return;
  }
  userInput.value = text;
  userInput.style.height = 'auto';
  sendMessage();
};

function sendMessage() {
  if (!authUser) {
    const accountTrigger = document.querySelector('.account-trigger');
    if (accountTrigger) accountTrigger.click();
    return;
  }
  const text = userInput.value.trim();
  if ((!text && !currentImageBase64 && !currentFaceBase64 && !currentAudioBase64 && !currentFileUpload) || isStreaming) return;
  
  loadingStatus.classList.remove('hidden');
  loadingText.textContent = "AI 正在思考...";

  // Append User Message to UI and State
  const chat = chats.find(c => c.id === currentChatId);
  chat.messages.push({
    role: 'user',
    content: text,
    imageBase64: currentImageBase64,
    faceBase64: currentFaceBase64,
    audioBase64: currentAudioBase64,
    fileUpload: currentFileUpload
  });
  saveChats();
  renderMessages(chat.messages);

  const mode = modeSwitch.checked ? 'expert' : 'fast';

  if (ws && ws.readyState === WebSocket.OPEN) {
    // 提取当前对话的历史记录（不包含当前刚发出的消息，且将系统消息转为 assistant）
    const history = chat.messages.slice(0, -1).map(m => ({
      role: m.role === 'system' ? 'assistant' : m.role,
      content: m.content
    }));

    ws.send(JSON.stringify({ 
      message: text, 
      mode: mode,
      image_data: currentImageBase64,
      face_data: currentFaceBase64,
      audio_data: currentAudioBase64,
      file_upload: currentFileUpload,
      history: history
    }));
  } else {
    alert("网络未连接，请检查后端服务。");
  }

  userInput.value = '';
  userInput.style.height = 'auto';
  userInput.style.overflowY = 'hidden';
  removeImageBtn.click();
  if (removeFaceBtn) removeFaceBtn.click();
  removeAudioBtn.click();
  removeFileBtn.click();
}

// Event Listeners
sendBtn.addEventListener('click', sendMessage);

const stopBtn = document.getElementById('stopBtn');
if (stopBtn) {
  stopBtn.addEventListener('click', () => {
    if (ws && isStreaming) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'cancel', task_id: ws.currentTaskId || undefined }));
      }
      isStreaming = false;
      stopBtn.classList.add('hidden');
      sendBtn.classList.remove('hidden');
      if (currentAssistantMessageDiv) {
        currentAssistantContent.innerHTML += '\n\n> 🛑 **[用户主动中止]**: 已中断当前回答。';
      }
    }
  });
}

userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Init
function installAuthAndAuditControls() {
  const accountDock = document.createElement('div');
  accountDock.className = 'account-dock';

  const authPanel = document.createElement('form');
  authPanel.className = 'account-menu hidden';
  authPanel.innerHTML = `
    <div class="account-menu__header">
      <span id="authMenuAvatar" class="account-avatar">未</span>
      <div>
        <strong id="authUserLabel">未登录</strong>
        <span id="authRoleLabel">访客会话</span>
      </div>
    </div>
    <div id="authFieldset" class="account-fieldset">
      <input id="authUsername" placeholder="用户名" autocomplete="username">
      <input id="authPassword" placeholder="密码" type="password" autocomplete="current-password">
    </div>
    <p id="authError" class="account-error hidden"></p>
    <div id="authLoginActions" class="account-menu__actions">
      <button id="authSubmitBtn" class="primary-action" type="submit">登录</button>
      <button id="authModeBtn" class="secondary-action" type="button">注册</button>
    </div>
    <div id="authSessionActions" class="account-menu__actions stacked hidden">
      <div id="authAuditSummary" class="account-audit-summary">
        <span><strong>0</strong>待审批</span>
        <span><strong>0</strong>运行中</span>
        <span><strong>0</strong>工具记录</span>
      </div>
      <button id="authAuditBtn" class="menu-action" type="button"><span>安全与审计</span><small>审批、任务、工具调用记录</small></button>
      <button id="authLogoutBtn" class="menu-action danger" type="submit"><span>退出登录</span></button>
    </div>
  `;
  accountDock.appendChild(authPanel);

  const accountTrigger = document.createElement('button');
  accountTrigger.className = 'account-trigger';
  accountTrigger.type = 'button';
  accountTrigger.innerHTML = `
    <span id="authTriggerAvatar" class="account-avatar">未</span>
    <span class="account-trigger__copy">
      <strong id="authTriggerUserLabel">未登录</strong>
      <small id="authTriggerRoleLabel">登录 / 注册</small>
    </span>
    <span class="account-trigger__chevron">⌃</span>
  `;
  accountDock.appendChild(accountTrigger);
  const sidebarAccountZone = document.getElementById('sidebarAccountZone');
  if (sidebarAccountZone) {
    sidebarAccountZone.appendChild(accountDock);
  } else {
    document.body.appendChild(accountDock);
  }

  const auditPanel = document.createElement('aside');
  auditPanel.className = 'governance-panel hidden';
  document.body.appendChild(auditPanel);

  let authMode = 'login';
  let governanceCache = { approvals: [], toolRuns: [], tasks: [] };
  const getAuthDisplayName = () => {
    if (!authUser) return '未登录';
    const opaqueUserId = /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(authUser.user_id || '');
    return authUser.username || (!opaqueUserId && authUser.user_id) || '企业用户';
  };
  const renderAuditSummary = () => {
    const summary = document.getElementById('authAuditSummary');
    if (!summary) return;
    const pending = (governanceCache.approvals || []).filter(item => item.status === 'pending').length;
    const active = (governanceCache.tasks || []).length;
    const toolRuns = (governanceCache.toolRuns || []).length;
    summary.innerHTML = `
      <span><strong>${pending}</strong>待审批</span>
      <span><strong>${active}</strong>运行中</span>
      <span><strong>${toolRuns}</strong>工具记录</span>
    `;
  };
  const loadGovernanceData = async () => {
    const [meRes, metricsRes, approvalsRes, toolRunsRes, tasksRes] = await Promise.all([
      fetch(getBackendUrl('/api/agent/auth/me'), { headers: authHeaders() }),
      fetch(getBackendUrl('/api/agent/metrics/governance'), { headers: authHeaders() }),
      fetch(getBackendUrl('/api/agent/audit/approvals?limit=10'), { headers: authHeaders() }),
      fetch(getBackendUrl('/api/agent/audit/tool-runs?limit=10'), { headers: authHeaders() }),
      fetch(getBackendUrl('/api/agent/tasks/active'), { headers: authHeaders() })
    ]);
    const [me, metrics, approvals, toolRuns, tasks] = await Promise.all([
      meRes.json(), metricsRes.json(), approvalsRes.json(), toolRunsRes.json(), tasksRes.json()
    ]);
    governanceCache = {
      me,
      metrics,
      approvals: approvals.items || [],
      toolRuns: toolRuns.items || [],
      tasks: tasks.items || []
    };
    renderAuditSummary();
    return governanceCache;
  };
  const renderIdentity = () => {
    const displayName = getAuthDisplayName();
    const roleLabel = authUser ? (authUser.roles || []).join(', ') : '访客会话';
    const initial = (displayName || 'G').slice(0, 1).toUpperCase();
    document.getElementById('authUserLabel').textContent = displayName;
    document.getElementById('authRoleLabel').textContent = roleLabel;
    document.getElementById('authTriggerUserLabel').textContent = displayName;
    document.getElementById('authTriggerRoleLabel').textContent = authUser ? roleLabel : '登录 / 注册';
    document.getElementById('authMenuAvatar').textContent = initial;
    document.getElementById('authTriggerAvatar').textContent = initial;
    document.getElementById('authMenuAvatar').classList.toggle('is-authenticated', Boolean(authUser));
    document.getElementById('authTriggerAvatar').classList.toggle('is-authenticated', Boolean(authUser));
    document.getElementById('authFieldset').classList.toggle('hidden', Boolean(authUser));
    document.getElementById('authLoginActions').classList.toggle('hidden', Boolean(authUser));
    document.getElementById('authSessionActions').classList.toggle('hidden', !authUser);
    document.getElementById('authSubmitBtn').textContent = authMode === 'login' ? '登录' : '创建账号';
    document.getElementById('authModeBtn').classList.toggle('hidden', Boolean(authUser));
    document.getElementById('authModeBtn').textContent = authMode === 'login' ? '注册' : '返回登录';
    userInput.disabled = !authUser;
    userInput.placeholder = authUser ? '输入您的问题或上传图片进行识别 (Shift+Enter 换行, Enter 发送)...' : '请先在左下角登录后使用企业 Agent';
    sendBtn.disabled = !authUser;
    document.querySelectorAll('.upload-btn, .mode-segment, .suggestion-chip').forEach(el => {
      el.disabled = !authUser;
    });
    if (!authUser) {
      wsStatus.innerHTML = '<span class="dot disconnected"></span> 请先登录';
    }
  };

  accountTrigger.addEventListener('click', () => {
    authPanel.classList.toggle('hidden');
    accountTrigger.classList.toggle('is-open', !authPanel.classList.contains('hidden'));
    if (authUser && !authPanel.classList.contains('hidden')) {
      loadGovernanceData().catch(error => console.warn('审计摘要加载失败:', error));
    }
  });

  authPanel.addEventListener('submit', async (event) => {
    event.preventDefault();
    const errorEl = document.getElementById('authError');
    errorEl.textContent = '';
    errorEl.classList.add('hidden');
    if (authUser) {
      authToken = '';
      authUser = null;
      localStorage.removeItem('talkweb_auth_token');
      localStorage.removeItem('talkweb_user_id');
      chats = [];
      if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
      }
      loadChats();
      authPanel.classList.add('hidden');
      accountTrigger.classList.remove('is-open');
      renderIdentity();
      return;
    }
    try {
      const res = await fetch(getBackendUrl(`/api/agent/auth/${authMode}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: document.getElementById('authUsername').value,
          password: document.getElementById('authPassword').value
        })
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail || '认证失败');
      authToken = payload.token;
      authUser = payload.user;
      localStorage.setItem('talkweb_auth_token', authToken);
      localStorage.setItem('talkweb_user_id', authUser.user_id);
      chats = [];
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
      loadChats();
      connectWebSocket();
      authPanel.classList.add('hidden');
      accountTrigger.classList.remove('is-open');
      renderIdentity();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove('hidden');
    }
  });

  document.getElementById('authModeBtn').addEventListener('click', () => {
    authMode = authMode === 'login' ? 'register' : 'login';
    renderIdentity();
  });

  document.getElementById('authAuditBtn').addEventListener('click', async () => {
    auditPanel.classList.toggle('hidden');
    authPanel.classList.add('hidden');
    accountTrigger.classList.remove('is-open');
    if (auditPanel.classList.contains('hidden')) return;
    const { me, approvals, toolRuns, tasks } = await loadGovernanceData();
    const pending = (approvals || []).filter(item => item.status === 'pending').length;
    auditPanel.innerHTML = `
      <div class="governance-panel__header">
        <div><h2>安全与审计</h2><p>${escapeHtml(me.user_id || 'unknown')} · 审批、任务、工具调用</p></div>
        <div class="governance-panel__actions">
          <button id="auditCloseBtn" type="button">关闭</button>
        </div>
      </div>
      <section><h3>概览</h3><div class="governance-metrics"><span>待审批: ${pending}</span><span>运行中: ${(tasks || []).length}</span><span>工具记录: ${(toolRuns || []).length}</span></div></section>
      <section><h3>活跃任务</h3><div class="governance-list">${(tasks || []).map(t => `<div class="governance-row"><strong>${escapeHtml(t.mode || '')}</strong><span>${escapeHtml(t.session_id || '')}</span><small>${t.age_seconds}s</small></div>`).join('') || '<p class="governance-empty">暂无活跃任务</p>'}</div></section>
      <section><h3>审批审计</h3><div class="governance-list">${(approvals || []).map(item => `<div class="governance-row"><strong>${escapeHtml(item.status || '')}</strong><span>${escapeHtml(item.approval_kind || '')}</span><small>${escapeHtml(item.requester_user_id || '')}</small></div>`).join('') || '<p class="governance-empty">暂无审批记录</p>'}</div></section>
      <section><h3>工具审计</h3><div class="governance-list">${(toolRuns || []).map(item => `<div class="governance-row"><strong>${escapeHtml(item.tool_name || '')}</strong><span>${escapeHtml(item.status || '')}</span><small>${item.duration_ms}ms</small></div>`).join('') || '<p class="governance-empty">暂无工具调用记录</p>'}</div></section>
    `;
    document.getElementById('auditCloseBtn').addEventListener('click', () => auditPanel.classList.add('hidden'));
  });

  window.renderAuthIdentity = renderIdentity;
  renderIdentity();
}

async function bootstrapAuth() {
  if (!authToken) return;
  const res = await fetch(getBackendUrl('/api/agent/auth/me'), { headers: authHeaders() });
  if (res.ok) {
    authUser = await res.json();
    localStorage.setItem('talkweb_user_id', authUser.user_id);
  }
}

installAuthAndAuditControls();
bootstrapAuth().finally(() => {
  if (window.renderAuthIdentity) window.renderAuthIdentity();
  loadChats();
  connectWebSocket();
});
