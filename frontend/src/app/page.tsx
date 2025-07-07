import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  BarChart3, 
  Upload, 
  MessageSquare, 
  TrendingUp, 
  Shield, 
  Zap,
  FileText,
  Brain
} from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gradient">RAGFin</h1>
                <p className="text-sm text-muted-foreground">AI-Powered Financial Analysis</p>
              </div>
            </div>
            <nav className="hidden md:flex items-center space-x-6">
              <Link href="/dashboard" className="text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/upload" className="text-muted-foreground hover:text-foreground transition-colors">
                Upload
              </Link>
              <Link href="/rag" className="text-muted-foreground hover:text-foreground transition-colors">
                Analysis
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h2 className="text-5xl font-bold tracking-tight mb-6">
            Intelligent Financial
            <span className="text-gradient"> Document Analysis</span>
          </h2>
          <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
            Transform your financial documents into actionable insights with AI-powered analysis. 
            Upload SEC filings, financial reports, and get instant, intelligent answers with proper citations.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="text-lg px-8 py-6">
              <Link href="/upload">
                <Upload className="w-5 h-5 mr-2" />
                Upload Documents
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="text-lg px-8 py-6">
              <Link href="/rag">
                <MessageSquare className="w-5 h-5 mr-2" />
                Start Analysis
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-4 py-20">
        <div className="grid md:grid-cols-3 gap-8">
          <Card className="card-hover">
            <CardHeader>
              <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center mb-4">
                <Upload className="w-6 h-6 text-blue-500" />
              </div>
              <CardTitle>Document Upload</CardTitle>
              <CardDescription>
                Securely upload PDF files, SEC filings, and financial reports. Our AI processes and indexes them for instant analysis.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                  <span>Drag & drop interface</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                  <span>Secure processing</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                  <span>Automatic indexing</span>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center mb-4">
                <Brain className="w-6 h-6 text-green-500" />
              </div>
              <CardTitle>AI-Powered Q&A</CardTitle>
              <CardDescription>
                Ask questions in natural language and get instant answers with proper citations from your uploaded documents.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                  <span>Natural language queries</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                  <span>Source citations</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                  <span>Real-time responses</span>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="card-hover">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-purple-500" />
              </div>
              <CardTitle>Analytics Dashboard</CardTitle>
              <CardDescription>
                View comprehensive analytics, document statistics, and insights from your financial documents.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-purple-500 rounded-full"></div>
                  <span>Document statistics</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-purple-500 rounded-full"></div>
                  <span>Processing insights</span>
                </li>
                <li className="flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-purple-500 rounded-full"></div>
                  <span>Usage analytics</span>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* How It Works */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h3 className="text-3xl font-bold mb-4">How It Works</h3>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Our AI-powered platform transforms your financial documents into actionable insights in three simple steps.
          </p>
        </div>
        
        <div className="grid md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-white">1</span>
            </div>
            <h4 className="font-semibold text-lg mb-2">Upload</h4>
            <p className="text-sm text-muted-foreground">
              Upload your financial documents through our secure interface
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-white">2</span>
            </div>
            <h4 className="font-semibold text-lg mb-2">Process</h4>
            <p className="text-sm text-muted-foreground">
              AI processes and indexes your documents for instant retrieval
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-white">3</span>
            </div>
            <h4 className="font-semibold text-lg mb-2">Query</h4>
            <p className="text-sm text-muted-foreground">
              Ask questions and get instant, cited answers from your documents
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-white">4</span>
            </div>
            <h4 className="font-semibold text-lg mb-2">Analyze</h4>
            <p className="text-sm text-muted-foreground">
              View analytics and insights from your document library
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <Card className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/20">
          <CardContent className="text-center py-16">
            <h3 className="text-3xl font-bold mb-4">Ready to Transform Your Financial Analysis?</h3>
            <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join financial professionals who are already using RAGFin to extract insights from their documents faster than ever.
            </p>
            <Button asChild size="lg" className="text-lg px-8 py-6">
              <Link href="/upload">
                <Upload className="w-5 h-5 mr-2" />
                Get Started Now
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
