export default function CalendarLoading() {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 h-10 w-72 animate-pulse rounded bg-slate-200" />
      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {Array.from({ length: 10 }).map((_, index) => (
          <div key={index} className="h-10 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
    </main>
  );
}
