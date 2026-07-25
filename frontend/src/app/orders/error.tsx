'use client';

export default function OrdersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-2xl rounded-xl border border-red-200 bg-red-50 p-6 text-red-800">
        <h1 className="text-xl font-semibold">Nepodarilo se nacist seznam zakazek</h1>
        <p className="mt-2 text-sm">{error.message || 'Necekavana chyba'}</p>
        <button onClick={reset} className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white">
          Zkusit znovu
        </button>
      </div>
    </main>
  );
}
