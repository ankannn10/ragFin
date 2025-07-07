'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Sidebar from '@/components/ui/Sidebar';
import useSWR from 'swr';
import { 
  BarChart3, 
  FileText, 
  TrendingUp, 
  Activity,
  Database,
  Clock,
  CheckCircle,
  AlertCircle,
  Download,
  Eye,
  Search,
  Upload
} from 'lucide-react';

const fetcher = (url: string) => fetch(url).then(r => r.json());

type Stats = {
  total_chunks: number;
  unique_documents: number;
  documents: string[];
};

export default function DashboardPage() {
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const { data, error, isLoading } = useSWR<Stats>('http://localhost:8000/rag/stats/', fetcher);

  const recentDocuments = data?.documents.slice(0, 5) || [];
  const processingStatus = 'completed'; // This would come from your backend

  return (
    <div className="flex h-screen bg-background">
      <Sidebar current={selectedDocument} onPick={setSelectedDocument} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center justify-between p-6">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
              <p className="text-muted-foreground">Analytics and insights from your documents</p>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export Data
              </Button>
              <Button size="sm">
                <Search className="w-4 h-4 mr-2" />
                New Analysis
              </Button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6">
          <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="card-hover">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {isLoading ? '...' : data?.unique_documents || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    +12% from last month
                  </p>
                </CardContent>
              </Card>

              <Card className="card-hover">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
                  <Database className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {isLoading ? '...' : data?.total_chunks || 0}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    +8% from last month
                  </p>
                </CardContent>
              </Card>

              <Card className="card-hover">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Processing Status</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm font-medium">All Complete</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Last updated 2 hours ago
                  </p>
                </CardContent>
              </Card>

              <Card className="card-hover">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">2.4 GB</div>
                  <p className="text-xs text-muted-foreground">
                    45% of available space
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Library Growth</CardTitle>
                <CardDescription>Documents indexed over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-48 bg-muted rounded-lg flex items-center justify-center text-sm text-muted-foreground">
                  Chart Placeholder
                </div>
              </CardContent>
            </Card>

            {/* Recent Activity and Document List */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Documents */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-5 h-5" />
                    <span>Recent Documents</span>
                  </CardTitle>
                  <CardDescription>
                    Recently uploaded and processed documents
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {isLoading ? (
                      <div className="space-y-3">
                        {[...Array(3)].map((_, i) => (
                          <div key={i} className="animate-pulse">
                            <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                            <div className="h-3 bg-muted rounded w-1/2"></div>
                          </div>
                        ))}
                      </div>
                    ) : recentDocuments.length === 0 ? (
                      <div className="text-center py-8">
                        <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-muted-foreground mb-4">No documents uploaded yet</p>
                        <Button size="sm">
                          <Upload className="w-4 h-4 mr-2" />
                          Upload First Document
                        </Button>
                      </div>
                    ) : (
                      recentDocuments.map((doc, index) => (
                        <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center">
                              <FileText className="w-4 h-4 text-blue-500" />
                            </div>
                            <div>
                              <p className="font-medium text-sm truncate max-w-[200px]">{doc}</p>
                              <p className="text-xs text-muted-foreground">Processed 2 hours ago</p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button variant="ghost" size="sm">
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Search className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Processing Status */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Activity className="w-5 h-5" />
                    <span>Processing Status</span>
                  </CardTitle>
                  <CardDescription>
                    Current status of document processing
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <div>
                          <p className="font-medium text-sm">All documents processed</p>
                          <p className="text-xs text-muted-foreground">Ready for analysis</p>
                        </div>
                      </div>
                      <span className="text-xs text-green-600 font-medium">Complete</span>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span>Documents indexed</span>
                        <span className="font-medium">{data?.unique_documents || 0}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span>Chunks created</span>
                        <span className="font-medium">{data?.total_chunks || 0}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span>Last update</span>
                        <span className="font-medium">2 hours ago</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common tasks and shortcuts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                    <Upload className="w-6 h-6" />
                    <span>Upload New Document</span>
                  </Button>
                  <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                    <Search className="w-6 h-6" />
                    <span>Start New Analysis</span>
                  </Button>
                  <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                    <BarChart3 className="w-6 h-6" />
                    <span>View Analytics</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}
