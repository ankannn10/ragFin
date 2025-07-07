'use client';
import { useState, useRef } from 'react';

export default function AskPanel({ file }: { file?: string }) {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  async function ask() {
    if (!query.trim()) return;
    setAnswer('');
    setLoading(true);

    try {
      // Use fetch + ReadableStream because Safari EventSource
      const res = await fetch('http://localhost:8000/rag/stream/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, filename: file, top_k: 5 }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const reader = res.body!.getReader();
      const decoder = new TextDecoder('utf-8');
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        setAnswer((a) => a + chunk);
      }
    } catch (error) {
      console.error('Error:', error);
      setAnswer('Sorry, there was an error processing your request. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      ask();
    }
  };

  return (
    <div className="space-y-6">
      {/* Query Input */}
      <div className="space-y-4">
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
            Ask a question about this document
          </label>
          <textarea
            id="query"
            className="w-full border border-gray-300 rounded-lg p-4 h-32 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="e.g. What are the main risk factors mentioned in this document? What are the key financial highlights? What are the company's growth strategies?"
            disabled={loading}
          />
          <p className="text-xs text-gray-500 mt-1">
            Press Cmd+Enter (Mac) or Ctrl+Enter (Windows) to submit
          </p>
        </div>
        
        <button
          onClick={ask}
          disabled={loading || !query.trim() || !file}
          className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </>
          ) : (
            <>
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Ask Question
            </>
          )}
        </button>
      </div>

      {/* Answer Display */}
      {answer && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              AI Response
            </h3>
            <button
              onClick={() => setAnswer('')}
              className="text-gray-400 hover:text-gray-600"
              title="Clear answer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="prose prose-sm max-w-none">
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <pre className="whitespace-pre-wrap text-gray-800 font-sans text-sm leading-relaxed">{answer}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && !answer && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-gray-600">Analyzing document and generating response...</span>
          </div>
        </div>
      )}
    </div>
  );
}
