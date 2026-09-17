import React, { useRef, useEffect } from 'react';
import { ImagePlus, X, Square, Send, Paperclip, FileText, FileAudio, UserCheck } from 'lucide-react';

const ChatInput = ({ 
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
  isAuthenticated,
  onRequireAuth
}) => {
  const fileInputRef = useRef(null);
  const audioInputRef = useRef(null);
  const faceInputRef = useRef(null);
  const textareaRef = useRef(null);

  const onFileChange = (e) => {
    if (!isAuthenticated) {
      onRequireAuth?.();
      e.target.value = '';
      return;
    }
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
          
          setImageBase64(canvas.toDataURL('image/jpeg', 0.8));
          setFileUpload(null); // Clear other files if image is selected
          setAudioBase64(null);
          if (setFaceBase64) setFaceBase64(null);
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
        setFileUpload({
          name: file.name,
          type: fileType,
          data: event.target.result
        });
        setImageBase64(null); // Clear image if other file is selected
        setAudioBase64(null);
        if (setFaceBase64) setFaceBase64(null);
      };
      reader.readAsDataURL(file);
    }
    e.target.value = '';
  };

  const onFaceChange = (e) => {
    if (!isAuthenticated) {
      onRequireAuth?.();
      e.target.value = '';
      return;
    }
    const file = e.target.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      if (setFaceBase64) setFaceBase64(event.target.result);
      setImageBase64(null);
      setFileUpload(null);
      setAudioBase64(null);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isAuthenticated) {
        onRequireAuth?.();
        return;
      }
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      if (textareaRef.current.scrollHeight >= 200) {
        textareaRef.current.style.overflowY = 'auto';
      } else {
        textareaRef.current.style.overflowY = 'hidden';
      }
      if (inputText === '') {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.overflowY = 'hidden';
      }
    }
  }, [inputText]);

  return (
    <div className="input-area glassmorphism">
      <div id="loadingStatus" className={`loading-status ${!isStreaming ? 'hidden' : ''}`}>
        <span>AI 正在思考...</span>
      </div>
      <div className="input-wrapper">
        {imageBase64 && (
          <div id="imagePreviewContainer" className="image-preview-container">
            <img id="imagePreview" src={imageBase64} alt="Preview" />
            <button id="removeImageBtn" className="remove-image-btn" onClick={() => {
              setImageBase64(null);
              if (fileInputRef.current) fileInputRef.current.value = '';
              if (audioInputRef.current) audioInputRef.current.value = '';
            }}>
              <X size={14} />
            </button>
          </div>
        )}

        {faceBase64 && (
          <div id="facePreviewContainer" className="image-preview-container" style={{ marginLeft: '12px', background: 'rgba(255,140,0,0.2)', padding: '4px 12px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid rgba(255,165,0,0.4)' }}>
            <span style={{ color: '#ffa500', fontWeight: 'bold' }}>👤 人脸核心核验图片</span>
            <img src={faceBase64} alt="Face Preview" style={{ height: '28px', width: '28px', objectFit: 'cover', borderRadius: '50%', border: '1px solid rgba(255,165,0,0.8)' }} />
            <button className="remove-image-btn" onClick={() => {
              if (setFaceBase64) setFaceBase64(null);
              if (faceInputRef.current) faceInputRef.current.value = '';
            }} style={{ position: 'relative', background: 'transparent' }}>
              <X size={14} />
            </button>
          </div>
        )}
        
        {audioBase64 && (
          <div id="audioPreviewContainer" className="image-preview-container" style={{ marginLeft: '12px', background: 'rgba(100,200,100,0.2)', padding: '4px 12px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🎵 语音已录制</span>
            <button className="remove-image-btn" onClick={() => setAudioBase64(null)} style={{ position: 'relative', background: 'transparent' }}>
              <X size={14} />
            </button>
          </div>
        )}
        
        {fileUpload && (
          <div id="filePreviewContainer" className="image-preview-container" style={{ marginLeft: '12px', background: fileUpload.type?.includes('audio') || /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(fileUpload.name) ? 'rgba(82, 196, 26, 0.2)' : 'rgba(100,150,250,0.2)', padding: '4px 12px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {fileUpload.type?.includes('audio') || /\.(mp3|wav|m4a|ogg|flac|webm|aac)$/i.test(fileUpload.name) ? <FileAudio size={16} style={{ color: '#52c41a' }} /> : <FileText size={16} />}
            <span>{fileUpload.name}</span>
            <button className="remove-image-btn" onClick={() => {
              setFileUpload(null);
              if (fileInputRef.current) fileInputRef.current.value = '';
              if (audioInputRef.current) audioInputRef.current.value = '';
            }} style={{ position: 'relative', background: 'transparent' }}>
              <X size={14} />
            </button>
          </div>
        )}
        
        <div className="input-row">
          <button id="uploadFileBtn" className="upload-btn" title={isAuthenticated ? '上传文档与图文 (OCR 智能提取)' : '登录后可上传'} disabled={!isAuthenticated} onClick={() => isAuthenticated ? fileInputRef.current?.click() : onRequireAuth?.()}>
            <Paperclip size={20} />
          </button>

          <button id="uploadFaceBtn" className="upload-btn" title={isAuthenticated ? '上传专属面相 (YOLOv8 + ArcFace 生物安全比对)' : '登录后可上传'} disabled={!isAuthenticated} onClick={() => isAuthenticated ? faceInputRef.current?.click() : onRequireAuth?.()}>
            <UserCheck size={20} style={{ color: '#ffa500' }} />
          </button>
          
          <button 
            id="recordAudioBtn" 
            className="upload-btn" 
            title={isAuthenticated ? '上传语音文件（回转文字内容）' : '登录后可上传'} 
            disabled={!isAuthenticated}
            onClick={() => isAuthenticated ? audioInputRef.current?.click() : onRequireAuth?.()}
          >
            <FileAudio size={20} />
          </button>
          
          <input 
            type="file" 
            id="imageInput" 
            ref={fileInputRef} 
            accept="image/*, .pdf, .txt, .docx, .md, .xlsx, .csv, .json, .pptx, .html, .xml" 
            style={{ display: 'none' }} 
            onChange={onFileChange}
          />

          <input 
            type="file" 
            id="faceInput" 
            ref={faceInputRef} 
            accept="image/*" 
            style={{ display: 'none' }} 
            onChange={onFaceChange}
          />

          <input 
            type="file" 
            id="audioFileInput" 
            ref={audioInputRef} 
            accept="audio/*, .mp3, .wav, .m4a, .webm, .flac, .ogg, .aac" 
            style={{ display: 'none' }} 
            onChange={onFileChange}
          />
          
          <textarea 
            id="userInput" 
            ref={textareaRef}
            placeholder={isAuthenticated ? '输入您的问题或上传图片进行识别 (Shift+Enter 换行, Enter 发送)...' : '请先在左下角登录后使用企业 Agent'}
            rows="1"
            disabled={!isAuthenticated}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          
          {isStreaming ? (
            <button id="stopBtn" className="stop-btn" title="中止生成" style={{ marginRight: '8px' }} onClick={handleStop}>
              <Square size={20} />
            </button>
          ) : (
            <button id="sendBtn" className="send-btn" disabled={!isAuthenticated} onClick={isAuthenticated ? handleSend : onRequireAuth}>
              <Send size={20} />
            </button>
          )}
        </div>
      </div>
      
      <div className="mode-toggle-bottom">
        <span className="mode-label">运行模式:</span>
        <div className="mode-segmented" role="group" aria-label="运行模式">
          {[
            ['fast', '极速'],
            ['expert', '专家'],
            ['orchestrator', '编排'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`mode-segment ${mode === value ? 'active' : ''}`}
              disabled={!isAuthenticated}
              onClick={() => setMode(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
