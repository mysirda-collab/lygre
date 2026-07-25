'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { getStoredUser, logout, type AuthUser } from '@/lib/auth';

export function UserMenu() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  if (!user) return null;

  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <div className="text-right">
        <p className="text-xs text-slate-500">Přihlášený uživatel</p>
        <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
        <p className="text-xs uppercase tracking-wide text-slate-500">{user.role}</p>
      </div>
      <button
        onClick={async () => {
          await logout();
          router.replace('/login');
        }}
        className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
      >
        Odhlásit
      </button>
    </div>
  );
}
