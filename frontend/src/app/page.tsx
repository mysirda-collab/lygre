"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { UserMenu } from "@/components/UserMenu";
import { authFetch } from "@/lib/auth";

type Job = {
  id: number;
  job_number: string;
  status: string;
  priority: string;
  customer_name: string;
  technician?: string | null;
  installation_date?: string | null;
};

type DashboardSummary = {
  status_counts: Record<string, number>;
  recent_jobs: Job[];
  overdue_jobs: Job[];
  today_installations: Job[];
};

const statusTitle: Record<string, string> = {
  new: "Nove",
  scheduled: "Naplanovane",
  done: "Dokoncene",
  cancelled: "Zrusene",
};

function CompactJobList({ title, jobs }: { title: string; jobs: Job[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-600">{title}</h2>
      {jobs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500">Bez polozek.</div>
      ) : (
        <div className="space-y-2">
          {jobs.slice(0, 6).map((job) => (
            <Link key={job.id} href={`/orders/${job.id}`} className="block rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-900">{job.job_number}</span>
                <span className="text-xs text-slate-500">{job.priority}</span>
              </div>
              <div className="mt-1 text-sm text-slate-700">{job.customer_name}</div>
              <div className="mt-1 text-xs text-slate-500">{job.technician || "-"}</div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSummary = async () => {
      try {
        setLoading(true);
        const response = await authFetch("/api/v1/jobs/dashboard/summary");
        if (!response.ok) {
          throw new Error("Nepodarilo se nacist dashboard");
        }
        const data = (await response.json()) as DashboardSummary;
        setSummary(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Neocekavana chyba dashboardu");
      } finally {
        setLoading(false);
      }
    };

    void loadSummary();
  }, []);

  const statusCounts = summary?.status_counts || {};
  const statuses = ["new", "scheduled", "done", "cancelled"];

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">Lygre</p>
            <h1 className="text-3xl font-bold text-slate-900">Dashboard zakazek</h1>
          </div>
          <UserMenu />
        </div>

        {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <div className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {statuses.map((key) => (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{statusTitle[key]}</div>
              {loading ? (
                <div className="mt-3 h-8 w-16 animate-pulse rounded bg-slate-100" />
              ) : (
                <div className="mt-3 text-3xl font-bold text-slate-900">{statusCounts[key] || 0}</div>
              )}
            </div>
          ))}
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-72 animate-pulse rounded-xl border border-slate-200 bg-slate-100" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <CompactJobList title="Posledni vytvorene" jobs={summary?.recent_jobs || []} />
            <CompactJobList title="Po terminu" jobs={summary?.overdue_jobs || []} />
            <CompactJobList title="Dnesni montaze" jobs={summary?.today_installations || []} />
          </div>
        )}

        <div className="mt-6">
          <Link href="/orders" className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            Otevrit seznam zakazek
          </Link>
        </div>
      </div>
    </main>
  );
}
