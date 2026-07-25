'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { getStoredAccessToken } from '@/lib/auth';

const PUBLIC_PATHS = new Set(['/login']);

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getStoredAccessToken();
    const isPublicPath = pathname ? PUBLIC_PATHS.has(pathname) : false;

    if (!token && !isPublicPath) {
      router.replace('/login');
      return;
    }

    if (token && isPublicPath) {
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
