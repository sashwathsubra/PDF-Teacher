import React from 'react';

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileList({ files, onRemove }) {
  return (
    <ul className="space-y-2">
      {files.map(file => (
        <li
          key={file.name}
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white rounded-lg px-3 py-3 border border-gray-100"
        >
          <div className="flex items-center gap-2.5 min-w-0 w-full sm:w-auto">
            <span className="text-red-500 flex-shrink-0">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 18H17V16H7v2zm10-8h-4V4H7v6H3l9 9 9-9h-4V10z" fill="none"/>
                <path fillRule="evenodd" clipRule="evenodd"
                  d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM13 9V3.5L18.5 9H13z"
                />
              </svg>
            </span>
            <span className="text-sm text-gray-800 font-medium break-words truncate" title={file.name}>
              {file.name}
            </span>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0 w-full sm:w-auto justify-between">
            <span className="text-xs text-gray-400">{formatBytes(file.size)}</span>
            <button
              type="button"
              onClick={() => onRemove(file.name)}
              className="text-gray-300 hover:text-gray-500 transition-colors rounded"
              aria-label={`Remove ${file.name}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
