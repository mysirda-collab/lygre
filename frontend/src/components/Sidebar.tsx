"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/', label: 'Dashboard' },
  { href: '/orders', label: 'Zakázky' },
  { href: '/customers', label: 'Zákazníci' },
  { href: '/technicians', label: 'Technici' },
  { href: '/calendar', label: 'Kalendář' },
  { href: '/documents', label: 'Dokumenty' },
  { href: '/import-pdf', label: 'Import PDF' },
  { href: '/settings', label: 'Nastavení' },
];

export function Sidebar() {
  const pathname = usePathname();

  if (pathname === '/login') {
    return null;
  }

  return (
    <aside className="hidden h-screen w-64 flex-col border-r border-slate-200 bg-white p-6 lg:flex">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Lygre</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-900">Montážní ERP</h2>
      </div>
      <nav className="space-y-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
        Přihlášení bude přidáno v další fázi.
      </div>
    </aside>
  );
}
