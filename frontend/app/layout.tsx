import './globals.css';
import { Inter } from 'next/font/google';
import { cn } from '@/lib/utils';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ragFin Dashboard',
  description: 'AI-powered SEC filings analysis',
};

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={cn(inter.className, 'bg-background text-foreground antialiased')}>{children}</body>
    </html>
  );
} 