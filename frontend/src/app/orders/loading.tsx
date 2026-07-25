export default function OrdersLoading() {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 h-10 w-56 animate-pulse rounded bg-slate-200" />
      <div className="mb-4 h-24 animate-pulse rounded-xl border border-slate-200 bg-white" />
      <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-8 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
    </main>
  );
}
