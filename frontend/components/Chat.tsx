'use client';

import { useState, useRef, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

// Generate a unique session ID for this chat session
function generateSessionId(): string {
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Generate a unique session ID that persists for this component instance
  const sessionId = useMemo(() => generateSessionId(), []);

  async function sendMessage() {
    if (!input.trim()) return;
    const userMsg: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rag/stream/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMsg.content,
          session_id: sessionId 
        }),
      });
      if (!res.body) throw new Error('No response body');
      const reader = res.body.getReader();
      let assistantContent = '';
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        assistantContent += new TextDecoder().decode(value);
        setMessages((prev) => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (newMsgs[lastIdx].role === 'assistant') {
            newMsgs[lastIdx] = { role: 'assistant', content: assistantContent };
          }
          return newMsgs;
        });
        containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with session info */}
      <div className="border-b p-3 bg-card/50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Conversational Chat</h3>
          <span className="text-xs text-muted-foreground">
            Session: {sessionId.split('_').pop()}
          </span>
        </div>
      </div>
      
      <div ref={containerRef} className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm p-8">
            <p>Ask questions about the uploaded filings.</p>
            <p className="mt-2">💡 I remember our conversation - you can ask follow-up questions!</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={cn('whitespace-pre-wrap', m.role === 'user' ? 'text-primary' : 'text-foreground')}>
            <span className="font-medium">{m.role === 'user' ? 'You: ' : 'AI: '}</span>
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="text-muted-foreground text-sm">
            <span className="font-medium">AI: </span>
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}
      </div>
      
      <div className="border-t p-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !loading && sendMessage()}
          placeholder="Ask about a filing… (remembers context)"
          disabled={loading}
        />
        <Button onClick={sendMessage} disabled={loading || !input.trim()}>
          Send
        </Button>
      </div>
    </div>
  );
} 