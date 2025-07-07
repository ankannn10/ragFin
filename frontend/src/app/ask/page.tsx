'use client';
import { useState } from 'react';
import Sidebar from '@/components/ui/Sidebar';
import AskPanel from '@/components/AskPanel';

export default function AskPage() {
  const [file, setFile] = useState<string | null>(null);
  return (
    <div className="flex h-screen bg-background">
      <Sidebar current={file ?? undefined} onPick={setFile} />
      <main className="flex-1 p-6 overflow-auto">
        <h1 className="text-2xl font-bold mb-4">Ask AI</h1>
        <AskPanel file={file ?? undefined} />
      </main>
    </div>
  );
}
