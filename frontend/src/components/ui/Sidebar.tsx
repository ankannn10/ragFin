'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import useSWR from 'swr';
import { 
  BarChart3, 
  Upload, 
  MessageSquare, 
  FileText, 
  ChevronRight,
  Database,
  TrendingUp,
  Activity
} from 'lucide-react';

const fetcher = (url: string) => fetch(url).then(r => r.json());

type Stats = {
  total_chunks: number;
  unique_documents: number;
  documents: string[];
};

interface SidebarProps {
  current?: string;
  onPick?: (f: string) => void;
}

export default function Sidebar({ current, onPick }: SidebarProps) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { data, error, isLoading } = useSWR<Stats>('http://localhost:8000/rag/stats/', fetcher);

  const navigation = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: BarChart3,
      description: 'Analytics & Overview'
    },
    {
      name: 'Upload',
      href: '/upload',
      icon: Upload,
      description: 'Document Management'
    },
    {
      name: 'RAG Analysis',
      href: '/rag',
      icon: MessageSquare,
      description: 'AI-Powered Q&A'
    }
  ];

  return (
    <div className={cn(
      "flex flex-col bg-card border-r border-border transition-all duration-300",
      isCollapsed ? "w-16" : "w-80"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gradient">RAGFin</span>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded-md hover:bg-muted transition-colors"
        >
          <ChevronRight className={cn(
            "w-4 h-4 text-muted-foreground transition-transform",
            isCollapsed && "rotate-180"
          )} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200 group",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && (
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs opacity-70">{item.description}</div>
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Document Library */}
      {!isCollapsed && onPick && (
        <div className="border-t border-border p-4">
          <div className="flex items-center space-x-2 mb-4">
            <Database className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground">Document Library</h3>
          </div>

          {/* Stats */}
          {data && (
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-primary">{data.total_chunks}</div>
                <div className="text-xs text-muted-foreground">Chunks</div>
              </div>
              <div className="bg-muted/50 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-primary">{data.unique_documents}</div>
                <div className="text-xs text-muted-foreground">Documents</div>
              </div>
            </div>
          )}

          {/* Document List */}
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {isLoading && (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-8 bg-muted rounded"></div>
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="text-center py-4">
                <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">Failed to load</p>
              </div>
            )}

            {data && data.documents.length === 0 && (
              <div className="text-center py-4">
                <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-xs text-muted-foreground mb-2">No documents</p>
                <Link 
                  href="/upload" 
                  className="inline-flex items-center px-2 py-1 bg-primary text-primary-foreground text-xs rounded hover:bg-primary/90 transition-colors"
                >
                  <Upload className="w-3 h-3 mr-1" />
                  Upload
                </Link>
              </div>
            )}

            {data && data.documents.map((filename) => (
              <button
                key={filename}
                onClick={() => onPick(filename)}
                className={cn(
                  "w-full text-left p-2 rounded-lg transition-all duration-200 group",
                  current === filename
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm truncate">{filename}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Collapsed Document Indicator */}
      {isCollapsed && onPick && data && data.documents.length > 0 && (
        <div className="border-t border-border p-2">
          <div className="relative">
            <Database className="w-5 h-5 text-muted-foreground mx-auto" />
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full text-xs text-primary-foreground flex items-center justify-center">
              {data.unique_documents}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 