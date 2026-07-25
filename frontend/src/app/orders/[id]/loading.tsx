export default function OrderDetailLoading() {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 h-10 w-64 animate-pulse rounded bg-slate-200" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-white" />
        ))}
      </div>
    </main>
  );
}
