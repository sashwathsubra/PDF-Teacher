import React, { useState } from 'react';
import UploadScreen from './components/UploadScreen';
import ChatWindow from './components/ChatWindow';

export default function App() {
  // 'upload' | 'chat'
  const [screen, setScreen] = useState('upload');
  const [sessionId, setSessionId] = useState(null);
  const [processedFiles, setProcessedFiles] = useState([]);

  function handleSessionReady({ sessionId, processedFiles }) {
    setSessionId(sessionId);
    setProcessedFiles(processedFiles);
    setScreen('chat');
  }

  function handleUploadNew() {
    setSessionId(null);
    setProcessedFiles([]);
    setScreen('upload');
  }

  return (
    <div className="min-h-screen bg-white">
      {screen === 'upload' ? (
        <UploadScreen onSessionReady={handleSessionReady} />
      ) : (
        <ChatWindow
          sessionId={sessionId}
          processedFiles={processedFiles}
          onUploadNew={handleUploadNew}
        />
      )}
    </div>
  );
}
