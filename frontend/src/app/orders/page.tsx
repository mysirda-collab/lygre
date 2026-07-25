"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { authFetch } from "@/lib/auth";

interface Job {
  id: number;
  job_number: string;
  status: string;
  priority: "low" | "medium" | "high" | "urgent";
  customer_name: string;
  company?: string | null;
  phone?: string | null;
  email?: string | null;
  street?: string | null;
  city?: string | null;
  zip?: string | null;
  installation_date?: string | null;
  technician?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

interface JobFormState {
  id?: number;
  job_number: string;
  status: string;
  priority: string;
  customer_name: string;
  company: string;
  phone: string;
  email: string;
  street: string;
  city: string;
  zip: string;
  installation_date: string;
  technician: string;
  notes: string;
}

interface JobDetailResponse {
  job: Job;
  attachments: Array<{
    id: number;
    original_filename: string;
    uploaded_at: string;
    file_size: number;
    status: string;
  }>;
  audit_logs: Array<{
    id: number;
    action: string;
    details?: string | null;
    created_at: string;
  }>;
}

const emptyForm: JobFormState = {
  job_number: "",
  status: "new",
  priority: "medium",
  customer_name: "",
  company: "",
  phone: "",
  email: "",
  street: "",
  city: "",
  zip: "",
  installation_date: "",
  technician: "",
  notes: "",
};

const statusLabels: Record<string, string> = {
  new: "Nova",
  scheduled: "Naplanovana",
  done: "Dokoncena",
  cancelled: "Zrusena",
};

const statusStyles: Record<string, string> = {
  new: "bg-sky-100 text-sky-700",
  scheduled: "bg-amber-100 text-amber-700",
  done: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-rose-100 text-rose-700",
};

const priorityLabels: Record<string, string> = {
  low: "Nizka",
  medium: "Stredni",
  high: "Vysoka",
  urgent: "Urgentni",
};

const priorityStyles: Record<string, string> = {
  low: "bg-slate-100 text-slate-700",
  medium: "bg-cyan-100 text-cyan-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};

export default function OrdersPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [technician, setTechnician] = useState("");
  const [customer, setCustomer] = useState("");
  const [installationDateFrom, setInstallationDateFrom] = useState("");
  const [installationDateTo, setInstallationDateTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDesc, setSortDesc] = useState(true);

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detail, setDetail] = useState<JobDetailResponse | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<JobFormState>(emptyForm);

  const [loading, setLoading] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState("");

  const fetchJobs = async (nextPage = page) => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        skip: String((nextPage - 1) * pageSize),
        limit: String(pageSize),
        sort_by: sortBy,
        sort_desc: String(sortDesc),
      });

      if (search) params.set("search", search);
      if (status) params.set("status", status);
      if (priority) params.set("priority", priority);
      if (technician) params.set("technician", technician);
      if (customer) params.set("customer", customer);
      if (installationDateFrom) params.set("installation_date_from", new Date(installationDateFrom).toISOString());
      if (installationDateTo) params.set("installation_date_to", new Date(installationDateTo).toISOString());

      const response = await authFetch(`/api/v1/jobs?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Nepodarilo se nacist seznam zakazek");
      }
      const data: JobListResponse = await response.json();
      setJobs(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nastala chyba pri nacitani zakazek");
    } finally {
      setLoading(false);
    }
  };

  const fetchDetail = async (jobId: number) => {
    setDrawerLoading(true);
    setDetail(null);

    try {
      const response = await authFetch(`/api/v1/jobs/${jobId}/detail`);
      if (!response.ok) {
        throw new Error("Nepodarilo se nacist detail zakazky");
      }
      const data: JobDetailResponse = await response.json();
      setDetail(data);
    } catch {
      setToast("Detail zakazky nebyl nacten");
    } finally {
      setDrawerLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs(page);
  }, [page, pageSize, search, status, priority, technician, customer, installationDateFrom, installationDateTo, sortBy, sortDesc]);

  const openCreate = () => {
    setForm({ ...emptyForm });
    setIsModalOpen(true);
    setError("");
  };

  const openEdit = (job: Job) => {
    setSelectedJob(job);
    setForm({
      id: job.id,
      job_number: job.job_number,
      status: job.status,
      priority: job.priority,
      customer_name: job.customer_name,
      company: job.company || "",
      phone: job.phone || "",
      email: job.email || "",
      street: job.street || "",
      city: job.city || "",
      zip: job.zip || "",
      installation_date: job.installation_date ? job.installation_date.slice(0, 10) : "",
      technician: job.technician || "",
      notes: job.notes || "",
    });
    setIsModalOpen(true);
    setError("");
  };

  const openDrawer = (job: Job) => {
    setSelectedJob(job);
    setIsDrawerOpen(true);
    void fetchDetail(job.id);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");

    const payload = {
      ...form,
      installation_date: form.installation_date ? new Date(form.installation_date).toISOString() : null,
    };

    const url = form.id ? `/api/v1/jobs/${form.id}` : "/api/v1/jobs";
    const method = form.id ? "PUT" : "POST";

    const response = await authFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setError(data.detail || "Nepodarilo se ulozit zakazku");
      return;
    }

    setIsModalOpen(false);
    setForm({ ...emptyForm });
    setToast(form.id ? "Zakazka byla upravena" : "Zakazka byla vytvorena");
    await fetchJobs(page);
  };

  const handleDelete = async (jobId: number) => {
    const confirmed = window.confirm("Opravdu chcete smazat tuto zakazku?");
    if (!confirmed) return;

    const response = await authFetch(`/api/v1/jobs/${jobId}`, { method: "DELETE" });
    if (response.ok) {
      setToast("Zakazka byla smazana");
      await fetchJobs(page);
    } else {
      setToast("Smazani zakazky selhalo");
    }
  };

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Zakazky</h1>
          <p className="mt-2 text-sm text-slate-500">Server-side filtrovani, fulltext a editace zakazek.</p>
        </div>
        <button onClick={openCreate} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Nova zakazka</button>
      </div>

      <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Fulltext vyhledavani" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input value={customer} onChange={(event) => { setCustomer(event.target.value); setPage(1); }} placeholder="Klient" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input value={technician} onChange={(event) => { setTechnician(event.target.value); setPage(1); }} placeholder="Technik" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">Vsechny stavy</option>
            <option value="new">Nova</option>
            <option value="scheduled">Naplanovana</option>
            <option value="done">Dokoncena</option>
            <option value="cancelled">Zrusena</option>
          </select>
          <select value={priority} onChange={(event) => { setPriority(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">Vsechny priority</option>
            <option value="low">Nizka</option>
            <option value="medium">Stredni</option>
            <option value="high">Vysoka</option>
            <option value="urgent">Urgentni</option>
          </select>
          <input type="date" value={installationDateFrom} onChange={(event) => { setInstallationDateFrom(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" title="Datum montaze od" />
          <input type="date" value={installationDateTo} onChange={(event) => { setInstallationDateTo(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" title="Datum montaze do" />
          <button
            onClick={() => {
              setSearch("");
              setStatus("");
              setPriority("");
              setTechnician("");
              setCustomer("");
              setInstallationDateFrom("");
              setInstallationDateTo("");
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            Reset filtru
          </button>
        </div>
      </div>

      {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div className="text-sm text-slate-500">Celkem: {total}</div>
          <div className="flex gap-2">
            <select value={sortBy} onChange={(event) => { setSortBy(event.target.value); setPage(1); }} className="rounded-lg border border-slate-300 px-2 py-2 text-sm">
              <option value="created_at">Datum vytvoreni</option>
              <option value="updated_at">Datum upravy</option>
              <option value="installation_date">Datum montaze</option>
              <option value="customer_name">Jmeno zakaznika</option>
              <option value="job_number">Cislo zakazky</option>
            </select>
            <button onClick={() => setSortDesc((value) => !value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">{sortDesc ? "↓" : "↑"}</button>
          </div>
        </div>

        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Cislo</th>
              <th className="px-4 py-3 text-left font-semibold">Zakaznik</th>
              <th className="px-4 py-3 text-left font-semibold">Datum</th>
              <th className="px-4 py-3 text-left font-semibold">Technik</th>
              <th className="px-4 py-3 text-left font-semibold">Priorita</th>
              <th className="px-4 py-3 text-left font-semibold">Stav</th>
              <th className="px-4 py-3 text-left font-semibold">Akce</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {loading ? (
              Array.from({ length: 6 }).map((_, index) => (
                <tr key={index}>
                  <td colSpan={7} className="px-4 py-3">
                    <div className="h-6 animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center">
                  <div className="space-y-2">
                    <p className="font-medium text-slate-700">Zadne zakazky neodpovidaji filtru</p>
                    <p className="text-slate-500">Zkuste upravit fulltext, datum nebo stav.</p>
                  </div>
                </td>
              </tr>
            ) : jobs.map((job) => (
              <tr key={job.id} className="cursor-pointer hover:bg-slate-50" onClick={() => openDrawer(job)}>
                <td className="px-4 py-3 font-medium">{job.job_number}</td>
                <td className="px-4 py-3">
                  <div>{job.customer_name}</div>
                  <div className="text-slate-500">{job.company || "-"}</div>
                </td>
                <td className="px-4 py-3">{job.installation_date ? new Date(job.installation_date).toLocaleDateString("cs-CZ") : "-"}</td>
                <td className="px-4 py-3">{job.technician || "-"}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${priorityStyles[job.priority] || "bg-slate-100 text-slate-700"}`}>
                    {priorityLabels[job.priority] || job.priority}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyles[job.status] || "bg-slate-100 text-slate-700"}`}>
                    {statusLabels[job.status] || job.status}
                  </span>
                </td>
                <td className="px-4 py-3" onClick={(event) => event.stopPropagation()}>
                  <div className="flex gap-2">
                    <button onClick={() => openEdit(job)} className="text-sm font-medium text-slate-700">Upravit</button>
                    <button onClick={() => handleDelete(job.id)} className="text-sm font-medium text-red-600">Smazat</button>
                    <Link href={`/orders/${job.id}`} className="text-sm font-medium text-indigo-700">Detail</Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-500">
          <div>Stranka {page} / {totalPages}</div>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-50">Predchozi</button>
            <button disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-50">Dalsi</button>
          </div>
        </div>
      </div>

      {isDrawerOpen && selectedJob ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Detail zakazky</p>
                <h2 className="text-xl font-semibold">{selectedJob.job_number}</h2>
              </div>
              <button onClick={() => setIsDrawerOpen(false)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">Zavrit</button>
            </div>

            {drawerLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            ) : detail ? (
              <div className="space-y-4 text-sm text-slate-700">
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="font-semibold">Zakaznik</div>
                  <div>{detail.job.customer_name}</div>
                  <div className="text-slate-500">{detail.job.company || "-"}</div>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="font-semibold">Poznamky</div>
                  <div>{detail.job.notes || "-"}</div>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-2 font-semibold">Prilohy</div>
                  {detail.attachments.length === 0 ? <div className="text-slate-500">Bez priloh</div> : (
                    <div className="space-y-1">
                      {detail.attachments.map((attachment) => (
                        <div key={attachment.id} className="flex items-center justify-between gap-2">
                          <span>{attachment.original_filename}</span>
                          <span className="text-slate-500">{Math.round(attachment.file_size / 1024)} kB</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <div className="mb-2 font-semibold">Historie zmen</div>
                  {detail.audit_logs.length === 0 ? <div className="text-slate-500">Bez historie</div> : (
                    <div className="space-y-2">
                      {detail.audit_logs.map((log) => (
                        <div key={log.id} className="rounded border border-slate-200 p-2">
                          <div className="font-medium">{log.action}</div>
                          <div className="text-xs text-slate-500">{new Date(log.created_at).toLocaleString("cs-CZ")}</div>
                          <div>{log.details || "-"}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">Detail zakazky neni dostupny.</div>
            )}
          </div>
        </div>
      ) : null}

      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{form.id ? "Upravit zakazku" : "Nova zakazka"}</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-sm text-slate-500">Zavrit</button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <label className="text-sm font-medium text-slate-700">
                  Cislo zakazky
                  <input required value={form.job_number} onChange={(event) => setForm({ ...form, job_number: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Stav
                  <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
                    <option value="new">Nova</option>
                    <option value="scheduled">Naplanovana</option>
                    <option value="done">Dokoncena</option>
                    <option value="cancelled">Zrusena</option>
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Priorita
                  <select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2">
                    <option value="low">Nizka</option>
                    <option value="medium">Stredni</option>
                    <option value="high">Vysoka</option>
                    <option value="urgent">Urgentni</option>
                  </select>
                </label>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="mb-3 font-semibold">Zakaznik</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium text-slate-700">
                    Jmeno zakaznika
                    <input required value={form.customer_name} onChange={(event) => setForm({ ...form, customer_name: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Spolecnost
                    <input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Telefon
                    <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Email
                    <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="mb-3 font-semibold">Adresa a termin</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium text-slate-700">
                    Ulice
                    <input value={form.street} onChange={(event) => setForm({ ...form, street: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Mesto
                    <input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    PSC
                    <input value={form.zip} onChange={(event) => setForm({ ...form, zip: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700">
                    Datum montaze
                    <input type="date" value={form.installation_date} onChange={(event) => setForm({ ...form, installation_date: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                  <label className="text-sm font-medium text-slate-700 md:col-span-2">
                    Technik
                    <input value={form.technician} onChange={(event) => setForm({ ...form, technician: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
                  </label>
                </div>
              </div>
              <label className="text-sm font-medium text-slate-700">
                Poznamky
                <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Zrusit</button>
                <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Ulozit</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {toast ? <div className="fixed bottom-4 right-4 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">{toast}</div> : null}
    </main>
  );
}
