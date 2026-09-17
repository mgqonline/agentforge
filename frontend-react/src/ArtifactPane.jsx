import React from 'react';
import { X } from 'lucide-react';
import { LiveProvider, LiveError, LivePreview } from 'react-live';

const ArtifactPane = ({ artifact, setArtifact }) => {
  if (!artifact.isOpen) return null;

  const closePane = () => setArtifact({ ...artifact, isOpen: false });

  return (
    <div className="artifact-pane glassmorphism">
      <div className="artifact-header">
        <h3 style={{ margin: 0, fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          ✨ Artifacts Preview
        </h3>
        <button className="icon-btn" onClick={closePane}>
          <X size={20} />
        </button>
      </div>
      <div className="artifact-content">
        {(artifact.language === 'jsx' || artifact.language === 'tsx' || artifact.language === 'react') ? (
          <LiveProvider code={artifact.content}>
            <div className="live-preview-container">
              <LivePreview />
            </div>
            <div className="live-error-container">
              <LiveError />
            </div>
          </LiveProvider>
        ) : (
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', padding: '16px', margin: 0, height: '100%', overflowY: 'auto' }}>
            <code>{artifact.content}</code>
          </pre>
        )}
      </div>
    </div>
  );
};

export default ArtifactPane;
