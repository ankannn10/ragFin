'use client';
import { useState, useRef } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Loader2, Send } from 'lucide-react';

export default function AskPanel({ file }: { file?: string }) {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function ask() {
    if (!query.trim()) return;
    setAnswer('');
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/rag/stream/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, filename: file, top_k: 5 }),
      });
      if (!res.ok) throw new Error('Request failed');
      const reader = res.body!.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      while (!done) {
        const { value, done: d } = await reader.read();
        done = d;
        if (value) setAnswer((a) => a + decoder.decode(value));
      }
    } catch (err) {
      console.error(err);
      setAnswer('Sorry, an error occurred.');
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
      <Card>
        <CardContent className="space-y-4 p-6">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask a question about this document..."
            className="w-full bg-background border border-border rounded-md p-3 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            rows={4}
            disabled={loading}
          />
          <div className="flex justify-end">
            <Button onClick={ask} disabled={loading || !query.trim() || !file}>
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Ask
            </Button>
          </div>
        </CardContent>
      </Card>

      {answer && (
        <Card>
          <CardContent className="p-6 space-y-2">
            <p className="text-sm text-muted-foreground">Answer</p>
            <div className="whitespace-pre-wrap font-mono text-sm">{answer}</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
