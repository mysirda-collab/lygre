"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { UserMenu } from "@/components/UserMenu";
import { DashboardJob, DashboardSummary, getDashboardSummary } from "@/lib/services/dashboard";

const statusTitle: Record<string, string> = {
  new: "Nove",
  scheduled: "Naplanovane",
  done: "Dokoncene",
  cancelled: "Zrusene",
};

const pipelineTitle: Record<string, string> = {
  new_imports: "Nove importy",
  waiting_sms: "Ceka na SMS",
  waiting_reservation: "Ceka na rezervaci",
  reservation_confirmed: "Rezervace potvrzena",
  installation_today: "Instalace dnes",
  installation_tomorrow: "Instalace zitra",
  completed: "Dokonceno",
};

const pipelineOrder = [
  "new_imports",
  "waiting_sms",
  "waiting_reservation",
  "reservation_confirmed",
  "installation_today",
  "installation_tomorrow",
  "completed",
];

function CompactJobList({ title, jobs }: { title: string; jobs: DashboardJob[] }) {
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
        setError(null);
        const data = await getDashboardSummary();
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
  const pipelineCounts = summary?.pipeline_counts || {};
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
            <a key={key} href={`/jobs?status=${key}`} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm block hover:shadow">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{statusTitle[key]}</div>
              {loading ? (
                <div className="mt-3 h-8 w-16 animate-pulse rounded bg-slate-100" />
              ) : (
                <div className="mt-3 text-3xl font-bold text-slate-900">{statusCounts[key] || 0}</div>
              )}
            </a>
          ))}
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {pipelineOrder.map((key) => (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{pipelineTitle[key]}</div>
              {loading ? (
                <div className="mt-3 h-8 w-16 animate-pulse rounded bg-slate-100" />
              ) : (
                <div className="mt-3 text-3xl font-bold text-slate-900">{pipelineCounts[key] || 0}</div>
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
