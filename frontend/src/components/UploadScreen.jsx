import React, { useState, useRef } from 'react';
import axios from 'axios';
import FileList from './FileList';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadScreen({ onSessionReady }) {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState('');
  const inputRef = useRef(null);

  const totalSize = files.reduce((acc, f) => acc + f.size, 0);
  const overLimit = totalSize > MAX_SIZE_BYTES;

  function addFiles(newFiles) {
    setError('');
    const pdfFiles = Array.from(newFiles).filter(f => f.type === 'application/pdf' || f.name.endsWith('.pdf'));
    if (pdfFiles.length !== newFiles.length) {
      setError('Only PDF files are accepted.');
    }
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      const unique = pdfFiles.filter(f => !existing.has(f.name));
      return [...prev, ...unique];
    });
  }

  function removeFile(name) {
    setFiles(prev => prev.filter(f => f.name !== name));
    setError('');
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }

  async function handleProcess() {
    if (overLimit) {
      setError(`Total size (${formatBytes(totalSize)}) exceeds the 50 MB limit. Please remove some files.`);
      return;
    }
    if (files.length === 0) return;

    setIsProcessing(true);
    setError('');
    setProgress('Extracting text from PDFs…');

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    try {
      setProgress('Embedding content and building index…');
      const { data } = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setProgress('');
      onSessionReady({
        sessionId: data.session_id,
        processedFiles: data.processed_files,
        skippedFiles: data.skipped_files,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || 'Upload failed. Please try again.';
      setError(detail);
      setProgress('');
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-accent-600">📄</span>
            <span className="font-semibold text-gray-900 text-base tracking-tight">PDF Teacher</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-500">
            <a href="#" className="hover:text-gray-800 transition-colors">How it works</a>
            <a href="#" className="hover:text-gray-800 transition-colors">About</a>
          </div>
        </div>
      </nav>

      {/* Hero + Upload */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-20 fade-in">
        <div className="w-full max-w-xl text-center">
          {/* Heading */}
          <h1 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight leading-tight">
            Ask Your PDFs
          </h1>
          <p className="text-gray-400 text-base mb-10 leading-relaxed">
            Upload your study material and ask questions<br className="hidden sm:block" /> like you would ask a teacher.
          </p>

          {/* Drop zone / file list area */}
          {files.length === 0 ? (
            /* Empty state — big upload target */
            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed rounded-2xl px-8 py-14 cursor-pointer
                transition-all duration-200
                ${isDragging
                  ? 'border-accent-400 bg-accent-50'
                  : 'border-gray-200 hover:border-accent-300 hover:bg-gray-50'}
              `}
            >
              <div className="flex flex-col items-center gap-4">
                <div className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors ${isDragging ? 'bg-accent-100' : 'bg-gray-100'}`}>
                  <svg className={`w-7 h-7 ${isDragging ? 'text-accent-500' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div>
                  <button
                    type="button"
                    className="bg-accent-600 hover:bg-accent-700 text-white font-semibold text-sm px-6 py-2.5 rounded-lg transition-colors"
                  >
                    Select PDF files
                  </button>
                  <p className="text-xs text-gray-400 mt-3">or drop PDFs here · up to 50 MB total</p>
                </div>
              </div>
            </div>
          ) : (
            /* Files selected state */
            <div className="slide-up">
              <div className="bg-gray-50 rounded-2xl p-5 mb-4 text-left">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-700">
                    {files.length} {files.length === 1 ? 'file' : 'files'} selected
                  </span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${overLimit ? 'bg-red-100 text-red-600' : 'bg-gray-200 text-gray-500'}`}>
                    {formatBytes(totalSize)} / 50 MB
                  </span>
                </div>
                <FileList files={files} onRemove={removeFile} />
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="mt-3 text-xs text-accent-600 hover:text-accent-700 font-medium transition-colors"
                >
                  + Add more PDFs
                </button>
              </div>

              <button
                type="button"
                onClick={handleProcess}
                disabled={isProcessing || overLimit || files.length === 0}
                className="w-full bg-accent-600 hover:bg-accent-700 disabled:bg-accent-300 text-white font-semibold text-base py-3.5 rounded-xl transition-all duration-200 flex items-center justify-center gap-2"
              >
                {isProcessing ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                    <span>{progress || 'Processing…'}</span>
                  </>
                ) : (
                  'Process & Start Chat →'
                )}
              </button>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3 text-left fade-in">
              {error}
            </div>
          )}
        </div>
      </main>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="hidden"
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />
    </div>
  );
}
