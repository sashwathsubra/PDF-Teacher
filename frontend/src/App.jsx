import React, { useState, useEffect } from 'react';
import UploadScreen from './components/UploadScreen';
import ChatWindow from './components/ChatWindow';

export default function App() {
  // 'upload' | 'chat'
  const [screen, setScreen] = useState('upload');
  const [sessionId, setSessionId] = useState(null);
  const [processedFiles, setProcessedFiles] = useState([]);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('pdf-teacher-session');
      if (saved) {
        const data = JSON.parse(saved);
        if (data?.sessionId && Array.isArray(data?.processedFiles)) {
          setSessionId(data.sessionId);
          setProcessedFiles(data.processedFiles);
          setScreen('chat');
        }
      }
    } catch (err) {
      console.warn('Failed to restore session storage', err);
    }
  }, []);

  function saveSessionStorage(sessionId, processedFiles) {
    sessionStorage.setItem(
      'pdf-teacher-session',
      JSON.stringify({ sessionId, processedFiles })
    );
  }

  function clearSessionStorage() {
    sessionStorage.removeItem('pdf-teacher-session');
  }

  function handleSessionReady({ sessionId, processedFiles }) {
    setSessionId(sessionId);
    setProcessedFiles(processedFiles);
    setScreen('chat');
    saveSessionStorage(sessionId, processedFiles);
  }

  function handleUploadNew() {
    setSessionId(null);
    setProcessedFiles([]);
    setScreen('upload');
    clearSessionStorage();
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
