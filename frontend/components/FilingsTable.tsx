'use client';

import { useEffect, useState } from 'react';

export default function FilingsTable() {
  const [docs, setDocs] = useState<string[]>([]);

  async function fetchStats() {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rag/stats`);
      const json = await res.json();
      setDocs(json.documents || []);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border rounded-md">
        <thead>
          <tr className="bg-card text-left">
            <th className="p-3">Filename</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((doc) => (
            <tr key={doc} className="border-t border-muted">
              <td className="p-3">{doc}</td>
              <td className="p-3">
                <span className="text-green-500">Processed</span>
              </td>
            </tr>
          ))}
          {docs.length === 0 && (
            <tr>
              <td className="p-3" colSpan={2}>
                No filings processed yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
} 