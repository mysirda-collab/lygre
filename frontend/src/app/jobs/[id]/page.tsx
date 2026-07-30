"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authFetch } from "@/lib/auth";

const STATUSES = ["Nová", "Vyžaduje kontrolu", "Klient nekontaktován", "Klient kontaktován", "Čeká na termín", "Termín naplánován", "Probíhá realizace", "Dokončeno", "Zrušeno"];

type Job = { id:number; job_number:string; customer_name:string; customer_id?:number; status:string; priority:string; phone?:string|null; email?:string|null; street?:string|null; city?:string|null; zip?:string|null; order_number?:string|null; parser_confidence:number; created_at:string };
type Detail = {
  job: Job;
  customer?: { id:number; customer_number:string; name:string; phone?:string|null; email?:string|null; street?:string|null; city?:string|null; zip?:string|null } | null;
  status_history: { id:number; previous_status?:string|null; new_status:string; changed_at:string }[];
  notes: { id:number; text:string; author_name?:string|null; created_at:string; updated_at?:string|null; updated_by_name?:string|null }[];
  attachments: { id:number; original_filename:string; source_original_filename?:string|null; uploaded_at:string; status:string; page_number?:number|null; total_pages?:number|null; parsed_data?:Record<string, unknown>|null; error_message?:string|null }[];
};

export default function JobDetailPage() {
  const { id } = useParams() as { id:string };
  const router = useRouter();
  const [detail, setDetail] = useState<Detail|null>(null);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [editingNote, setEditingNote] = useState<{id:number; text:string}|null>(null);
  const [error, setError] = useState<string|null>(null);
  const [success, setSuccess] = useState<string|null>(null);

  const load = useCallback(async () => {
    const response = await authFetch(`/api/v1/jobs/${id}/detail`);
    if (!response.ok) throw new Error("Zakázku se nepodařilo načíst");
    const data: Detail = await response.json();
    setDetail(data); setStatus(data.job.status);
  }, [id]);
  useEffect(() => { void load().catch(error => setError(String(error))); }, [load]);

  const changeStatus = async () => {
    const response = await authFetch(`/api/v1/jobs/${id}/status`, { method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({status}) });
    if (!response.ok) return setError("Stav se nepodařilo uložit");
    await load();
  };
  const addNote = async () => {
    if (!note.trim()) return;
    setError(null); setSuccess(null);
    const response = await authFetch(`/api/v1/jobs/${id}/notes`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:note}) });
    if (!response.ok) return setError("Poznámku se nepodařilo uložit");
    setNote(""); setSuccess("Poznámka byla přidána."); await load();
  };
  const updateNote = async () => {
    if (!editingNote?.text.trim()) return setError("Poznámka nesmí být prázdná");
    setError(null); setSuccess(null);
    const response = await authFetch(`/api/v1/jobs/${id}/notes/${editingNote.id}`, { method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:editingNote.text}) });
    if (!response.ok) return setError("Změny poznámky se nepodařilo uložit");
    setEditingNote(null); setSuccess("Poznámka byla upravena."); await load();
  };

  if (!detail) return <div className="p-4">{error || "Načítání…"}</div>;
  const { job, customer } = detail;
  const parsed = detail.attachments.length ? "Dostupné v detailu importu" : "Bez zdrojového importu";
  return <div className="space-y-5 p-4">
    <button className="border px-3 py-1" onClick={() => router.push("/jobs")}>Zpět</button>
    {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
    {success && <div className="rounded border border-green-200 bg-green-50 p-3 text-green-700">{success}</div>}
    <header><h1 className="text-2xl font-semibold">Zakázka {job.job_number}</h1><p>Aktuální stav: <strong>{job.status}</strong></p></header>
    <div className="grid gap-4 md:grid-cols-2">
      <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Zákazník</h2>
        {customer ? <><a className="text-blue-600 hover:underline" href={`/customers/${customer.id}`}>{customer.name}</a><p>Číslo: {customer.customer_number}</p><p>{customer.phone} · {customer.email}</p><p>{customer.street}, {customer.zip} {customer.city}</p></> : <p>{job.customer_name}</p>}
      </section>
      <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Informace o zakázce</h2><p>Objednávka: {job.order_number || "—"}</p><p>Priorita: {job.priority}</p><p>Adresa: {job.street}, {job.zip} {job.city}</p><p>Vytvořeno: {new Date(job.created_at).toLocaleString()}</p></section>
    </div>
    <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Změnit stav</h2><div className="flex gap-2"><select className="border p-2" value={status} onChange={e=>setStatus(e.target.value)}>{!STATUSES.includes(status) && <option value={status}>{status}</option>}{STATUSES.map(item=><option key={item}>{item}</option>)}</select><button className="border px-3" onClick={changeStatus}>Uložit stav</button></div></section>
    <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Historie stavů</h2>{detail.status_history.length ? <ul className="space-y-1">{detail.status_history.map(item=><li key={item.id}>{new Date(item.changed_at).toLocaleString()}: {item.previous_status || "—"} → <strong>{item.new_status}</strong></li>)}</ul> : <p className="text-slate-500">Bez historie</p>}</section>
    <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Poznámky</h2><label className="block text-sm font-medium" htmlFor="new-job-note">Nová poznámka</label><div className="mt-1 flex gap-2"><textarea id="new-job-note" className="min-h-20 flex-1 border p-2" value={note} onChange={e=>setNote(e.target.value)}/><button className="border px-3" onClick={addNote} disabled={!note.trim()}>Přidat poznámku</button></div><ul className="mt-3 space-y-3">{detail.notes.map(item=><li key={item.id} className="border-t pt-3">{editingNote?.id === item.id ? <div className="space-y-2"><textarea className="min-h-20 w-full border p-2" value={editingNote.text} onChange={e=>setEditingNote({...editingNote, text:e.target.value})}/><div className="flex gap-2"><button className="border px-3 py-1" onClick={updateNote}>Uložit změny</button><button className="border px-3 py-1" onClick={()=>setEditingNote(null)}>Zrušit</button></div></div> : <><p className="whitespace-pre-wrap">{item.text}</p><p className="mt-1 text-xs text-slate-500">Vytvořil/a {item.author_name || "Neznámý uživatel"} · {new Date(item.created_at).toLocaleString()}</p>{item.updated_at && <p className="text-xs text-slate-500">Naposledy upravil/a {item.updated_by_name || "Neznámý uživatel"} · {new Date(item.updated_at).toLocaleString()}</p>}<button className="mt-2 border px-3 py-1 text-sm" onClick={()=>setEditingNote({id:item.id, text:item.text})}>Upravit</button></>}</li>)}</ul></section>
    <section className="rounded-xl border bg-white p-4"><h2 className="mb-2 font-semibold">Zdrojový PDF import</h2><p className="text-sm">Parsování: {parsed}; důvěra {Math.round(job.parser_confidence * 100)} %; {job.status === "Vyžaduje kontrolu" ? "vyžaduje kontrolu" : "bez příznaku kontroly"}.</p><ul className="mt-2 space-y-3">{detail.attachments.map(file=><li key={file.id}><a className="text-blue-600" href={`/api/v1/uploads/pdf/${file.id}/download`}>{file.source_original_filename || file.original_filename}</a> · strana {file.page_number || 1}/{file.total_pages || 1} · {file.status}{file.error_message && <p className="text-red-600">{file.error_message}</p>}{file.parsed_data && <pre className="mt-1 overflow-auto rounded bg-slate-50 p-2 text-xs">{JSON.stringify(file.parsed_data, null, 2)}</pre>}</li>)}</ul></section>
  </div>;
}
