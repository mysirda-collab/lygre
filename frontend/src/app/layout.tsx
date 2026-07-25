import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { AuthGate } from '@/components/AuthGate';

export const metadata: Metadata = {
  title: 'Lygre',
  description: 'ERP pro správu zakázek a montáží',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs">
      <body>
        <AuthGate>
          <div className="flex min-h-screen bg-slate-50">
            <Sidebar />
            <div className="flex-1">{children}</div>
          </div>
        </AuthGate>
      </body>
    </html>
  );
}
