import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import MessageBubble from './MessageBubble';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ChatWindow({ sessionId, processedFiles, onUploadNew }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initial welcome message
  useEffect(() => {
    const fileNames = processedFiles?.join(', ') || 'your PDFs';
    setMessages([
      {
        role: 'ai',
        text: `Hi! I've finished reading ${processedFiles?.length > 1 ? `${processedFiles.length} files` : fileNames}. Ask me anything from your uploaded material — I'll answer like your teacher would.`,
        sources: [],
      },
    ]);
    inputRef.current?.focus();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendMessage() {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput('');
    setError('');

    // Add user message
    setMessages(prev => [...prev, { role: 'user', text: question, sources: [] }]);

    // Add typing indicator
    setIsLoading(true);
    setMessages(prev => [...prev, { role: 'typing', text: '', sources: [] }]);

    try {
      const { data } = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        question,
      });

      // Remove typing indicator, add AI response
      setMessages(prev => [
        ...prev.filter(m => m.role !== 'typing'),
        { role: 'ai', text: data.answer, sources: data.sources },
      ]);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Something went wrong. Please try again.';
      setMessages(prev => prev.filter(m => m.role !== 'typing'));
      setError(detail);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Top bar */}
      <header className="border-b border-gray-100 bg-white flex-shrink-0">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">📄</span>
            <span className="font-semibold text-gray-900 text-sm">PDF Teacher Assistant</span>
          </div>
          <button
            onClick={onUploadNew}
            className="text-xs font-medium text-accent-600 hover:text-accent-700 transition-colors flex items-center gap-1.5 hover:underline underline-offset-2"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Upload New PDFs
          </button>
        </div>
      </header>

      {/* Loaded files indicator */}
      {processedFiles?.length > 0 && (
        <div className="border-b border-gray-50 bg-gray-50 flex-shrink-0">
          <div className="max-w-3xl mx-auto px-4 py-2 flex items-center gap-1.5 flex-wrap">
            <svg className="w-3 h-3 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5..." />
            </svg>
            <span className="text-xs text-gray-400">Reading from:</span>
            {processedFiles.map((name, i) => (
              <span key={i} className="text-xs font-medium text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto custom-scroll">
        <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              text={msg.text}
              sources={msg.sources}
            />
          ))}
          {error && (
            <div className="text-sm text-red-500 bg-red-50 border border-red-100 rounded-lg px-4 py-2.5 fade-in">
              {error}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input bar */}
      <footer className="border-t border-gray-100 bg-white flex-shrink-0">
        <div className="max-w-2xl mx-auto px-4 py-4">
          {/* Disclaimer */}
          <p className="text-center text-xs text-gray-300 mb-3">
            I only answer using your uploaded PDFs
          </p>
          <div className="flex items-end gap-3 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 focus-within:border-accent-300 focus-within:ring-2 focus-within:ring-accent-100 transition-all">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => {
                setInput(e.target.value);
                // Auto-resize
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question from your PDFs…"
              className="flex-1 bg-transparent text-sm text-gray-800 placeholder-gray-400 resize-none outline-none leading-relaxed min-h-[24px] max-h-[120px]"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 w-8 h-8 rounded-lg bg-accent-600 hover:bg-accent-700 disabled:bg-gray-200 text-white disabled:text-gray-400 flex items-center justify-center transition-all"
              aria-label="Send message"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
