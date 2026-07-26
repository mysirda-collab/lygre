import Link from 'next/link';

export default function ReservationInvalidPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto mt-20 max-w-xl rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-900">Odkaz na rezervaci je neplatny</h1>
        <p className="mt-3 text-sm text-slate-600">
          Rezervacni token je neplatny nebo expirovany. Kontaktujte prosim dispecink.
        </p>
        <div className="mt-6">
          <Link href="/" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            Zpet na uvod
          </Link>
        </div>
      </div>
    </main>
  );
}
