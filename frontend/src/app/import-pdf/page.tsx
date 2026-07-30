'use client';

import Link from 'next/link';
import { ChangeEvent, DragEvent, useEffect, useMemo, useState } from 'react';

import { apiUrl } from '@/lib/api';
import { authFetch } from '@/lib/auth';

interface UploadItem {
  id: number;
  original_filename: string;
  uploaded_at: string;
  status: string;
  file_size: number;
  content_type?: string | null;
  extracted_text?: string | null;
  parsed_data?: Record<string, string | boolean> | string | null;
  job_id?: number | null;
  processing_status?: string | null;
  processing_progress?: number | null;
  processing_message?: string | null;
  source_document_id?: string | null;
  source_original_filename?: string | null;
  page_number?: number | null;
  total_pages?: number | null;
}

interface UploadCreateResponse {
  id: number;
  created_ids?: number[];
  created_count?: number;
}

const statusStyles: Record<string, string> = {
  'Čeká na zpracování': 'bg-slate-100 text-slate-700',
  'Zpracovává se': 'bg-amber-100 text-amber-700',
  Hotovo: 'bg-emerald-100 text-emerald-700',
  Chyba: 'bg-rose-100 text-rose-700',
  'Vyžaduje kontrolu': 'bg-rose-100 text-rose-700',
};

export default function ImportPdfPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetchUploads = async () => {
    const response = await authFetch('/api/v1/uploads/pdf');
    if (response.ok) {
      const data = await response.json();
      setUploads(data);
    }
  };

  useEffect(() => {
    fetchUploads();
  }, []);


  useEffect(() => {
    const hasPending = uploads.some(
      (u) =>
        u.processing_status !== "Hotovo" &&
        u.processing_status !== "Vyžaduje kontrolu" &&
        u.processing_status !== "Chyba"
    );

    if (!hasPending) return;

    const timer = window.setInterval(fetchUploads, 2000);

    return () => window.clearInterval(timer);
  }, [uploads]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    const dropped = event.dataTransfer.files?.[0] ?? null;
    setFile(dropped);
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    const response = await authFetch('/api/v1/uploads/pdf', {
      method: 'POST',
      body: formData,
    });

    setLoading(false);

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setMessage(data.detail || 'Nahrání selhalo');
      return;
    }

    const data: UploadCreateResponse = await response.json().catch(() => ({ id: 0 }));

    await fetchUploads();
    const createdCount = data.created_count ?? data.created_ids?.length ?? 1;
    setMessage(`PDF nahráno: ${file.name} (${createdCount} záznam${createdCount === 1 ? '' : createdCount < 5 ? 'y' : 'ů'})`);
    setFile(null);
  };

  const totalSize = useMemo(() => uploads.reduce((sum, item) => sum + item.file_size, 0), [uploads]);

  const sourceSummaries = useMemo(() => {
    const map = new Map<
      string,
      {
        sourceName: string;
        totalPages: number;
        uploadCount: number;
        createdJobs: number;
        progressTotal: number;
        activeMessage: string | null;
      }
    >();
    for (const upload of uploads) {
      const key = upload.source_document_id || `single-${upload.id}`;
      const sourceName = upload.source_original_filename || upload.original_filename;
      const totalPages = upload.total_pages || 1;
      const progress = upload.processing_progress ?? 0;
      const existing = map.get(key);
      if (!existing) {
        map.set(key, {
          sourceName,
          totalPages,
          uploadCount: 1,
          createdJobs: upload.job_id ? 1 : 0,
          progressTotal: progress,
          activeMessage: upload.processing_message || null,
        });
      } else {
        existing.uploadCount += 1;
        existing.createdJobs += upload.job_id ? 1 : 0;
        existing.progressTotal += progress;
        if (upload.processing_message && progress < 100) {
          existing.activeMessage = upload.processing_message;
        }
      }
    }
    return Array.from(map.values()).map((summary) => ({
      ...summary,
      progress: Math.round(summary.progressTotal / Math.max(summary.uploadCount, 1)),
    }));
  }, [uploads]);

  const parseParsedData = (upload: UploadItem) => {
    if (!upload.parsed_data) return null;
    if (typeof upload.parsed_data === 'object') return upload.parsed_data;
    try {
      return JSON.parse(upload.parsed_data);
    } catch {
      return null;
    }
  };

  return (
    <main className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Import PDF</h1>
        <p className="mt-2 text-sm text-slate-500">Nahrajte PDF se zakázkou a zapište je do evidence.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`rounded-xl border-2 border-dashed p-8 text-center transition ${dragActive ? 'border-slate-900 bg-slate-50' : 'border-slate-300'}`}
          >
            <p className="text-lg font-semibold">Přetáhněte PDF sem</p>
            <p className="mt-2 text-sm text-slate-500">Nebo vyberte soubor z počítače.</p>
            <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
              Vybrat soubor
              <input type="file" accept="application/pdf" className="hidden" onChange={handleFileChange} />
            </label>
            {file ? <p className="mt-4 text-sm text-slate-600">Vybraný soubor: {file.name}</p> : null}
          </div>

          {loading ? (
            <div className="mt-6">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-600">
                <span>Odesílám PDF na server…</span>
                <span>0%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-200">
                <div className="h-2 rounded-full bg-slate-900 transition-all" style={{ width: '0%' }} />
              </div>
            </div>
          ) : null}

          <div className="mt-6 flex items-center gap-3">
            <button onClick={handleUpload} disabled={!file || loading} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50">
              Nahrát PDF
            </button>
            {message ? <span className="text-sm text-slate-600">{message}</span> : null}
          </div>
        </section>

        <aside className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Evidence PDF</h2>
          <p className="mt-2 text-sm text-slate-500">Celkem nahráno: {uploads.length}</p>
          <p className="mt-1 text-sm text-slate-500">Celková velikost: {(totalSize / 1024 / 1024).toFixed(2)} MB</p>
          <div className="mt-4 space-y-2 text-sm text-slate-600">
            {sourceSummaries.length === 0 ? (
              <p>Zatím bez historie importů.</p>
            ) : sourceSummaries.map((summary) => (
              <div key={`${summary.sourceName}-${summary.totalPages}-${summary.uploadCount}`} className="rounded-lg border border-slate-200 bg-slate-50 p-2">
                <div className="font-medium text-slate-700">{summary.sourceName}</div>
                <div>Stran: {summary.totalPages} · Vytvořené listy: {summary.uploadCount}</div>
                <div>
                  Vytvořené zakázky: {summary.createdJobs} / {summary.uploadCount}
                </div>
                <div className="mt-2">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span>{summary.activeMessage || 'Stav zpracování'}</span>
                    <span>{summary.progress}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-200">
                    <div className="h-1.5 rounded-full bg-slate-900 transition-all" style={{ width: `${summary.progress}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Nahrané PDF</h2>
          <span className="text-sm text-slate-500">Seznam a historie uploadů</span>
        </div>
        <div className="space-y-3">
          {uploads.length === 0 ? (
            <p className="text-sm text-slate-500">Zatím nebylo nahráno žádné PDF.</p>
          ) : uploads.map((upload) => {
            const parsed = parseParsedData(upload);
            return (
              <div key={upload.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <button onClick={() => window.open(apiUrl(`/api/v1/uploads/pdf/${upload.id}/file`), '_blank')} className="text-left text-sm font-semibold text-slate-900 underline-offset-2 hover:underline">
                      {upload.original_filename}
                    </button>
                    <div className="mt-1 text-sm text-slate-500">
                      {new Date(upload.uploaded_at).toLocaleString('cs-CZ')} · {(upload.file_size / 1024).toFixed(1)} KB
                    </div>
                    {upload.source_original_filename ? (
                      <div className="mt-1 text-xs text-slate-500">
                        Zdroj: {upload.source_original_filename} · Strana {upload.page_number || 1}/{upload.total_pages || 1}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyles[upload.status] || 'bg-slate-100 text-slate-700'}`}>
                      {upload.status}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                      {upload.processing_status || 'Zpracovává se'}
                    </span>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>{upload.processing_message || 'Stav zpracování není k dispozici'}</span>
                    <span>{upload.processing_progress ?? 0}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-200">
                    <div className="h-2 rounded-full bg-slate-900 transition-all" style={{ width: `${upload.processing_progress ?? 0}%` }} />
                  </div>
                </div>

                {parsed ? (
                  <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <div className="font-medium">Nalezené údaje</div>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <div>Zakázka: {parsed.job_number || '—'}</div>
                      <div>Zákazník: {parsed.customer_name || '—'}</div>
                      <div>Telefon: {parsed.phone || '—'}</div>
                      <div>E-mail: {parsed.email || '—'}</div>
                      <div>Ulice: {parsed.street || '—'}</div>
                      <div>Město/PSČ: {parsed.city || '—'} {parsed.zip ? `, ${parsed.zip}` : ''}</div>
                    </div>
                  </div>
                ) : null}

                <div className="mt-4 flex flex-wrap gap-3">
                  {upload.job_id ? (
                    <Link href={`/orders/${upload.job_id}`} className="text-sm font-medium text-slate-700 underline-offset-2 hover:underline">
                      Otevřít zakázku
                    </Link>
                  ) : null}
                  {upload.status === 'Vyžaduje kontrolu' ? (
                    <Link href={`/import-pdf/review/${upload.id}`} className="text-sm font-medium text-slate-700 underline-offset-2 hover:underline">
                      Opravit údaje
                    </Link>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
