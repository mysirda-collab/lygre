'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

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
  parsed_data?: ParsedData | string | null;
  job_id?: number | null;
  processing_status?: string | null;
}

interface ParsedData {
  job_number?: string;
  customer_name?: string;
  phone?: string;
  email?: string;
  street?: string;
  city?: string;
  zip?: string;
  should_create_job?: boolean;
}

const initialForm = {
  job_number: '',
  customer_name: '',
  phone: '',
  email: '',
  street: '',
  city: '',
  zip: '',
  status: 'new',
};

export default function ReviewUploadPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [upload, setUpload] = useState<UploadItem | null>(null);
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadUpload = async () => {
      const response = await authFetch(`/api/v1/uploads/pdf/${params.id}`);
      if (!response.ok) return;
      const data = await response.json();
      setUpload(data);
      if (data.parsed_data) {
        let parsed: ParsedData | null = null;
        if (typeof data.parsed_data === 'string') {
          try {
            parsed = JSON.parse(data.parsed_data) as ParsedData;
          } catch {
            parsed = null;
          }
        } else {
          parsed = data.parsed_data;
        }
        if (!parsed) {
          return;
        }
        setForm({
          job_number: parsed.job_number || '',
          customer_name: parsed.customer_name || '',
          phone: parsed.phone || '',
          email: parsed.email || '',
          street: parsed.street || '',
          city: parsed.city || '',
          zip: parsed.zip || '',
          status: 'new',
        });
      }
    };
    void loadUpload();
  }, [params.id]);

  const previewText = useMemo(() => upload?.extracted_text || 'Žádný text nebyl extrahován.', [upload]);
  const fileUrl = useMemo(() => (upload ? apiUrl(`/api/v1/uploads/pdf/${upload.id}/file`) : null), [upload]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);

    const response = await authFetch(`/api/v1/uploads/pdf/${params.id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });

    setSaving(false);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setMessage(data.detail || 'Uložení selhalo');
      return;
    }

    const job = await response.json();
    setMessage(`Zakázka uložena: ${job.job_number}`);
    router.push(`/orders/${job.id}`);
  };

  return (
    <main className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Kontrola PDF</h1>
          <p className="mt-2 text-sm text-slate-500">Zkontrolujte a opravte nalezené údaje před vytvořením zakázky.</p>
        </div>
        <Link href="/import-pdf" className="text-sm font-medium text-slate-700 underline-offset-2 hover:underline">
          Zpět na import
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Náhled PDF</h2>
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            {fileUrl ? (
              <iframe src={fileUrl} title="PDF náhled" className="h-[640px] w-full" />
            ) : (
              <div className="p-4 text-sm text-slate-700">Načítám soubor…</div>
            )}
          </div>
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            <p className="font-medium">Extrahovaný text</p>
            <p className="mt-2 whitespace-pre-wrap">{previewText}</p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Údaje zakázky</h2>
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium text-slate-700">
                Číslo zakázky
                <input value={form.job_number} onChange={(event) => setForm({ ...form, job_number: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Jméno zákazníka
                <input value={form.customer_name} onChange={(event) => setForm({ ...form, customer_name: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Telefon
                <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                E-mail
                <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Ulice
                <input value={form.street} onChange={(event) => setForm({ ...form, street: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                Město
                <input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="text-sm font-medium text-slate-700">
                PSČ
                <input value={form.zip} onChange={(event) => setForm({ ...form, zip: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
              </label>
            </div>

            <div className="flex items-center gap-3">
              <button type="submit" disabled={saving} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {saving ? 'Ukládám…' : 'Potvrdit a vytvořit zakázku'}
              </button>
              {message ? <span className="text-sm text-slate-600">{message}</span> : null}
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
