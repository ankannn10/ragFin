'use client';

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Sidebar from '@/components/ui/Sidebar';
import useSWR from 'swr';
import { 
  Send, 
  MessageSquare, 
  FileText, 
  Bot, 
  User, 
  Copy,
  CheckCircle,
  AlertCircle,
  Loader2,
  Sparkles
} from 'lucide-react';

const fetcher = (url: string) => fetch(url).then(r => r.json());

type Stats = {
  total_chunks: number;
  unique_documents: number;
  documents: string[];
};

type Message = {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: string[];
};

export default function RAGPage() {
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { data, error, isLoading: statsLoading } = useSWR<Stats>('http://localhost:8000/rag/stats/', fetcher);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/rag/stream_answer/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: inputValue,
          filename: selectedDocument || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      let assistantMessage = '';
      const assistantMessageId = (Date.now() + 1).toString();

      // Add initial assistant message
      setMessages(prev => [...prev, {
        id: assistantMessageId,
        type: 'assistant',
        content: '',
        timestamp: new Date(),
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        assistantMessage += chunk;

        // Update the assistant message
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: assistantMessage }
            : msg
        ));
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="flex h-screen bg-background">
      <Sidebar current={selectedDocument} onPick={setSelectedDocument} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center justify-between p-6">
            <div>
              <h1 className="text-2xl font-bold text-foreground">AI Analysis</h1>
              <p className="text-muted-foreground">
                Ask questions about your financial documents
                {selectedDocument && (
                  <span className="ml-2 text-primary">
                    • Analyzing: {selectedDocument}
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {statsLoading ? (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Loading...</span>
                </div>
              ) : data && data.documents.length === 0 ? (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <AlertCircle className="w-4 h-4" />
                  <span>No documents uploaded</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <FileText className="w-4 h-4" />
                  <span>{data?.unique_documents || 0} documents available</span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="w-8 h-8 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Start Your Analysis</h3>
                  <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                    Ask questions about your financial documents and get instant, AI-powered answers with proper citations.
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                    <Card className="card-hover cursor-pointer" onClick={() => setInputValue("What are the key financial highlights from the latest quarter?")}>
                      <CardContent className="p-4">
                        <p className="text-sm">"What are the key financial highlights from the latest quarter?"</p>
                      </CardContent>
                    </Card>
                    <Card className="card-hover cursor-pointer" onClick={() => setInputValue("What are the main risks mentioned in the risk factors section?")}>
                      <CardContent className="p-4">
                        <p className="text-sm">"What are the main risks mentioned in the risk factors section?"</p>
                      </CardContent>
                    </Card>
                    <Card className="card-hover cursor-pointer" onClick={() => setInputValue("What is the company's revenue growth trend over the past 3 years?")}>
                      <CardContent className="p-4">
                        <p className="text-sm">"What is the company's revenue growth trend over the past 3 years?"</p>
                      </CardContent>
                    </Card>
                    <Card className="card-hover cursor-pointer" onClick={() => setInputValue("What are the key strategic initiatives mentioned in the management discussion?")}>
                      <CardContent className="p-4">
                        <p className="text-sm">"What are the key strategic initiatives mentioned in the management discussion?"</p>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-3xl ${message.type === 'user' ? 'order-2' : 'order-1'}`}>
                      <Card className={`${message.type === 'user' ? 'bg-primary text-primary-foreground' : 'bg-card'}`}>
                        <CardContent className="p-4">
                          <div className="flex items-start space-x-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                              message.type === 'user' 
                                ? 'bg-primary-foreground/20' 
                                : 'bg-primary/10'
                            }`}>
                              {message.type === 'user' ? (
                                <User className="w-4 h-4" />
                              ) : (
                                <Bot className="w-4 h-4 text-primary" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">
                                  {message.type === 'user' ? 'You' : 'AI Assistant'}
                                </span>
                                <div className="flex items-center space-x-2">
                                  <span className="text-xs opacity-70">
                                    {message.timestamp.toLocaleTimeString()}
                                  </span>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => copyToClipboard(message.content)}
                                    className="h-6 w-6 p-0"
                                  >
                                    <Copy className="w-3 h-3" />
                                  </Button>
                                </div>
                              </div>
                              <div className="prose prose-sm max-w-none">
                                <p className="whitespace-pre-wrap">{message.content}</p>
                              </div>
                              {message.sources && message.sources.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-border/50">
                                  <p className="text-xs font-medium mb-2">Sources:</p>
                                  <div className="space-y-1">
                                    {message.sources.map((source, index) => (
                                      <div key={index} className="text-xs opacity-70 flex items-center space-x-1">
                                        <FileText className="w-3 h-3" />
                                        <span>{source}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </div>
                ))
              )}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-3xl">
                    <Card>
                      <CardContent className="p-4">
                        <div className="flex items-start space-x-3">
                          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                            <Bot className="w-4 h-4 text-primary" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <span className="text-sm font-medium">AI Assistant</span>
                              <Loader2 className="w-4 h-4 animate-spin" />
                            </div>
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-border bg-card/50 backdrop-blur-sm p-6">
            <div className="max-w-4xl mx-auto">
              <div className="flex space-x-4">
                <div className="flex-1">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask a question about your financial documents..."
                    className="w-full p-3 border border-border rounded-lg bg-background text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    rows={1}
                    style={{ minHeight: '44px', maxHeight: '120px' }}
                    disabled={isLoading}
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  size="lg"
                  className="px-6"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-muted-foreground">
                  Press Enter to send, Shift+Enter for new line
                </p>
                {selectedDocument && (
                  <p className="text-xs text-primary">
                    Analyzing: {selectedDocument}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
