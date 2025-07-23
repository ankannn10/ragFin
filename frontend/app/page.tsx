import Sidebar from '@/components/Sidebar';
import UploadDropzone from '@/components/UploadDropzone';
import Chat from '@/components/Chat';
import FilingsTable from '@/components/FilingsTable';
import MetricsCard from '@/components/MetricsCard';

async function getStats() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rag/stats`, { cache: 'no-store' });
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const stats = await getStats();

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 overflow-y-auto h-screen p-6 space-y-6">
        <section className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          <MetricsCard title="Total Chunks" value={stats?.total_chunks ?? '--'} />
          <MetricsCard title="Unique Filings" value={stats?.unique_documents ?? '--'} />
          <MetricsCard title="Last Upload" value={stats?.documents?.slice(-1)[0] ?? '--'} />
        </section>
        <section>
          <h2 className="text-lg font-semibold mb-4">Upload Filing</h2>
          <UploadDropzone />
        </section>
        <section id="filings" className="space-y-4">
          <h2 className="text-lg font-semibold">Filings</h2>
          <FilingsTable />
        </section>
        <section id="chat" className="h-[600px]">
          <h2 className="text-lg font-semibold mb-4">Chat</h2>
          <div className="border rounded-lg h-full">
            <Chat />
          </div>
        </section>
      </main>
    </div>
  );
} 