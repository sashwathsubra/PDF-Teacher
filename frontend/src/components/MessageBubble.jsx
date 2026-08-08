import React, { useState } from 'react';

/**
 * Renders a single chat message.
 *
 * Props:
 *   role: 'user' | 'ai' | 'typing'
 *   text: string (AI answer)
 *   sources: [{filename, page}]
 */
export default function MessageBubble({ role, text, sources = [] }) {
  if (role === 'typing') {
    return (
      <div className="flex items-start gap-3 fade-in">
        <div className="w-7 h-7 rounded-full bg-accent-100 flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-accent-600 text-xs font-bold">T</span>
        </div>
        <div className="pt-2">
          <div className="flex items-center gap-0.5">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        </div>
      </div>
    );
  }

  if (role === 'user') {
    return (
      <div className="flex justify-end fade-in">
        <div className="max-w-[85%] bg-gray-100 text-gray-800 rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          {text}
        </div>
      </div>
    );
  }

  // AI message
  return (
    <div className="flex items-start gap-3 fade-in">
      <div className="w-7 h-7 rounded-full bg-accent-100 flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-accent-600 text-xs font-bold">T</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="relative">
          <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap" 
               dangerouslySetInnerHTML={{ __html: text }}
          />

          <div className="absolute top-0 right-0">
            <CopyButton text={text} />
          </div>
        </div>
        {sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {sources.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-50 border border-gray-100 rounded-md px-2 py-1"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
                {s.filename} · p.{s.page}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const plain = text.replace(/<[^>]+>/g, '');
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(plain);
      } else {
        const el = document.createElement('textarea');
        el.value = plain;
        el.setAttribute('readonly', '');
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('copy failed', e);
    }
  };

  return (
    <button
      onClick={handleCopy}
      title={copied ? 'Copied' : 'Copy'}
      className="ml-2 inline-flex items-center gap-1 bg-white/0 hover:bg-gray-50 border border-transparent hover:border-gray-100 rounded px-2 py-1 text-xs text-gray-500"
    >
      {copied ? (
        <span className="text-green-600">Copied</span>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6M9 7h6a2 2 0 012 2v8a2 2 0 01-2 2H9a2 2 0 01-2-2V9a2 2 0 012-2z" />
        </svg>
      )}
    </button>
  );
}
