
'use client';
import useSWR from 'swr';
import { cn } from '@/lib/utils';

const fetcher = (url: string) => fetch(url).then(r => r.json());

type Stats = {
  total_chunks: number;
  unique_documents: number;
  documents: string[];
};

export default function Sidebar({
  current,
  onPick,
}: {
  current?: string;
  onPick: (f: string) => void;
}) {
  const { data, error, isLoading } = useSWR<Stats>('http://localhost:8000/rag/stats/', fetcher);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Document Library</h2>
        <p className="text-sm text-gray-500">
          Select a document to analyze
        </p>
      </div>

      {/* Stats */}
      <div className="p-6 border-b border-gray-200">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-red-600 text-sm">Error loading stats</p>
          </div>
        )}
        
        {isLoading && (
          <div className="space-y-3">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        )}

        {data && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-600">{data.total_chunks}</div>
                <div className="text-xs text-blue-600 font-medium">Total Chunks</div>
              </div>
              <div className="bg-green-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-green-600">{data.unique_documents}</div>
                <div className="text-xs text-green-600 font-medium">Documents</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Available Documents</h3>
          
          {isLoading && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-8 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <p className="text-gray-500 text-sm">Failed to load documents</p>
            </div>
          )}

          {data && data.documents.length === 0 && (
            <div className="text-center py-8">
              <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-500 text-sm mb-4">No documents uploaded yet</p>
              <a 
                href="/upload" 
                className="inline-flex items-center px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Upload Documents
              </a>
            </div>
          )}

          {data && data.documents.length > 0 && (
            <div className="space-y-2">
              {data.documents.map((filename) => (
                <button
                  key={filename}
                  onClick={() => onPick(filename)}
                  className={cn(
                    'w-full text-left p-3 rounded-lg border transition-all duration-200 group',
                    current === filename
                      ? 'bg-blue-50 border-blue-200 text-blue-900 shadow-sm'
                      : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <div className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                        current === filename
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'
                      )}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={cn(
                          'text-sm font-medium truncate',
                          current === filename ? 'text-blue-900' : 'text-gray-900'
                        )}>
                          {filename}
                        </p>
                        <p className={cn(
                          'text-xs truncate',
                          current === filename ? 'text-blue-600' : 'text-gray-500'
                        )}>
                          PDF Document
                        </p>
                      </div>
                    </div>
                    {current === filename && (
                      <svg className="w-5 h-5 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
