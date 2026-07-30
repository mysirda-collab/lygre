'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

import { apiUrl } from '@/lib/api';
import { authFetch } from '@/lib/auth';

type Job = {
  id: number;
  job_number: string;
  status: string;
  priority: string;
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
};

type JobDetailResponse = {
  job: Job;
  notes: Array<{
    id: number;
    text: string;
    author_name?: string | null;
    created_at: string;
    updated_at?: string | null;
    updated_by_name?: string | null;
  }>;
  attachments: Array<{
    id: number;
    original_filename: string;
    uploaded_at: string;
    file_size: number;
    status: string;
    source_original_filename?: string | null;
    page_number?: number | null;
    total_pages?: number | null;
  }>;
  audit_logs: Array<{
    id: number;
    action: string;
    details?: string | null;
    created_at: string;
  }>;
};

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const [detail, setDetail] = useState<JobDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState('');
  const [editingNote, setEditingNote] = useState<{ id: number; text: string } | null>(null);
  const [noteMessage, setNoteMessage] = useState<string | null>(null);
  const [savingNote, setSavingNote] = useState(false);

  const loadJob = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await authFetch(`/api/v1/jobs/${params.id}/detail`);
      if (!response.ok) {
        setError('Zakazka nebyla nalezena.');
        return;
      }
      const data = (await response.json()) as JobDetailResponse;
      setDetail(data);
    } catch {
      setError('Detail zakazky se nepodarilo nacist.');
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void loadJob();
  }, [loadJob]);

  const addNote = async () => {
    const text = newNote.trim();
    if (!text) return;
    setSavingNote(true);
    setNoteMessage(null);
    try {
      const response = await authFetch(`/api/v1/jobs/${params.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error();
      setNewNote('');
      setNoteMessage('Poznámka byla přidána.');
      await loadJob();
    } catch {
      setNoteMessage('Poznámku se nepodařilo přidat.');
    } finally {
      setSavingNote(false);
    }
  };

  const updateNote = async () => {
    const text = editingNote?.text.trim();
    if (!editingNote || !text) return;
    setSavingNote(true);
    setNoteMessage(null);
    try {
      const response = await authFetch(`/api/v1/jobs/${params.id}/notes/${editingNote.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error();
      setEditingNote(null);
      setNoteMessage('Poznámka byla upravena.');
      await loadJob();
    } catch {
      setNoteMessage('Poznámku se nepodařilo upravit.');
    } finally {
      setSavingNote(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Detail zakazky</h1>
          <p className="mt-2 text-sm text-slate-500">Kompletni informace, historie a prilohy.</p>
        </div>
        <Link href="/orders" className="text-sm font-medium text-slate-700 underline-offset-2 hover:underline">
          Zpet na seznam
        </Link>
      </div>

      {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

      {loading ? (
        <div className="grid gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-white" />
          ))}
        </div>
      ) : detail ? (
        <div className="grid gap-4">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Cislo zakazky</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{detail.job.job_number}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Stav</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{detail.job.status}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Priorita</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{detail.job.priority}</p>
              </div>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Zakaznik</p>
                <p className="mt-1 text-slate-900">{detail.job.customer_name}</p>
                <p className="text-slate-600">{detail.job.company || '-'}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Kontakt</p>
                <p className="mt-1 text-slate-900">{detail.job.phone || '-'} · {detail.job.email || '-'}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Adresa</p>
                <p className="mt-1 text-slate-900">{detail.job.street || '-'}<br />{[detail.job.city, detail.job.zip].filter(Boolean).join(' ') || '-'}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Technik</p>
                <p className="mt-1 text-slate-900">{detail.job.technician || '-'}</p>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold">Poznámky</h2>
            <label htmlFor="new-note" className="text-sm font-medium text-slate-700">Nová poznámka</label>
            <textarea
              id="new-note"
              value={newNote}
              onChange={(event) => setNewNote(event.target.value)}
              className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
            />
            <button
              type="button"
              onClick={addNote}
              disabled={savingNote || !newNote.trim()}
              className="mt-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Přidat poznámku
            </button>
            {noteMessage ? <p className="mt-2 text-sm text-slate-700">{noteMessage}</p> : null}

            {detail.notes.length === 0 ? (
              <div className="mt-4 rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500">Zakázka zatím nemá žádné poznámky.</div>
            ) : (
              <div className="mt-4 space-y-3">
                {detail.notes.map((note) => (
                  <div key={note.id} className="rounded-lg border border-slate-200 p-3">
                    {editingNote?.id === note.id ? (
                      <>
                        <textarea
                          value={editingNote.text}
                          onChange={(event) => setEditingNote({ ...editingNote, text: event.target.value })}
                          className="min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
                        />
                        <div className="mt-2 flex gap-2">
                          <button type="button" onClick={updateNote} disabled={savingNote || !editingNote.text.trim()} className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50">Uložit změny</button>
                          <button type="button" onClick={() => setEditingNote(null)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">Zrušit</button>
                        </div>
                      </>
                    ) : (
                      <>
                        <p className="whitespace-pre-wrap text-sm text-slate-900">{note.text}</p>
                        <p className="mt-2 text-xs text-slate-500">{note.author_name || 'Neznámý uživatel'} · {new Date(note.created_at).toLocaleString('cs-CZ')}</p>
                        {note.updated_at ? <p className="text-xs text-slate-500">Upravil/a {note.updated_by_name || 'Neznámý uživatel'} · {new Date(note.updated_at).toLocaleString('cs-CZ')}</p> : null}
                        <button type="button" onClick={() => setEditingNote({ id: note.id, text: note.text })} className="mt-2 text-sm font-medium text-slate-700 underline-offset-2 hover:underline">Upravit</button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold">Prilohy</h2>
            {detail.attachments.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500">Zakazka zatim nema zadne prilohy.</div>
            ) : (
              <div className="space-y-2">
                {detail.attachments.map((attachment) => (
                  <div key={attachment.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
                    <div>
                      <div className="font-medium text-slate-900">{attachment.original_filename}</div>
                      <div className="text-slate-500">{new Date(attachment.uploaded_at).toLocaleString('cs-CZ')}</div>
                      {attachment.source_original_filename ? (
                        <div className="text-slate-500">
                          Zdroj: {attachment.source_original_filename} · Strana {attachment.page_number || 1}/{attachment.total_pages || 1}
                        </div>
                      ) : null}
                      <button
                        onClick={() => window.open(apiUrl(`/api/v1/uploads/pdf/${attachment.id}/source-file`), '_blank')}
                        className="mt-1 text-xs font-medium text-slate-700 underline-offset-2 hover:underline"
                      >
                        Otevřít původní PDF
                      </button>
                    </div>
                    <div className="text-slate-500">{Math.round(attachment.file_size / 1024)} kB</div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold">Historie zmen</h2>
            {detail.audit_logs.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-3 text-sm text-slate-500">Bez zaznamenanych zmen.</div>
            ) : (
              <div className="space-y-2">
                {detail.audit_logs.map((log) => (
                  <div key={log.id} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-slate-900">{log.action}</p>
                      <p className="text-xs text-slate-500">{new Date(log.created_at).toLocaleString('cs-CZ')}</p>
                    </div>
                    <p className="mt-1 text-sm text-slate-700">{log.details || '-'}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
