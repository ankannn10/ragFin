'use client';

import Link from 'next/link';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const navItems = [
  { title: 'Dashboard', href: '/' },
  { title: 'Chat', href: '#chat' },
  { title: 'Filings', href: '#filings' },
];

export default function Sidebar() {
  const [active, setActive] = useState('/');
  return (
    <aside className="flex flex-col w-56 h-screen bg-card border-r">
      <div className="p-6 text-xl font-bold">ragFin</div>
      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setActive(item.href)}
            className={cn(
              'block rounded-md px-3 py-2 text-sm font-medium transition-colors',
              active === item.href ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
            )}
          >
            {item.title}
          </Link>
        ))}
      </nav>
      <div className="p-4 text-xs text-muted-foreground">
        © {new Date().getFullYear()} ragFin
      </div>
    </aside>
  );
} 