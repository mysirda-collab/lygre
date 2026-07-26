'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { getStoredAccessToken } from '@/lib/auth';

function isPublicPath(pathname: string | null): boolean {
  if (!pathname) return false;
  return pathname === '/login' || pathname.startsWith('/reservation');
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getStoredAccessToken();
    const publicPath = isPublicPath(pathname);

    if (!token && !publicPath) {
      router.replace('/login');
      return;
    }

    if (token && pathname === '/login') {
      router.replace('/');
      return;
    }

    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return <div className="p-6 text-sm text-slate-500">Načítám…</div>;
  }

  return <>{children}</>;
}
