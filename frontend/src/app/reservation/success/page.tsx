"use client";

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

export default function ReservationSuccessPage() {
  const search = useSearchParams();
  const token = search.get('token');

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto mt-20 max-w-xl rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Rezervace byla potvrzena</h1>
        <p className="mt-3 text-sm text-slate-600">
          Dekujeme. Potvrzeni terminu bylo uspesne zpracovano.
        </p>
        {token ? (
          <div className="mt-6">
            <Link href={`/reservation/${token}`} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
              Zobrazit detail rezervace
            </Link>
          </div>
        ) : null}
      </div>
    </main>
  );
}
