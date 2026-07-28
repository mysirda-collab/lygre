"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authFetch } from '@/lib/auth';

type Customer = { id: number; name: string; phone?: string | null; email?: string | null; street?: string | null; city?: string | null; zip?: string | null; created_at?: string }
type Job = { id: number; job_number: string; status: string; created_at?: string; installation_date?: string | null }
type Reservation = { id: number; status: string; starts_at?: string; created_at?: string }

export default function CustomerDetailPage(){
  const params = useParams() as { id?: string };
  const id = params.id as string;
  const router = useRouter();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState({ name: '', phone: '', email: '', street: '', city: '', zip: '' });
  const [toast, setToast] = useState<string | null>(null);

  useEffect(()=>{
    const load = async ()=>{
      try{
        setLoading(true);
        const [resCust, resJobs, resRes] = await Promise.all([
          authFetch(`/api/v1/customers/${id}`),
          authFetch(`/api/v1/jobs?customer_id=${id}&limit=50`),
          authFetch(`/api/v1/customers/${id}/reservations`),
        ]);
        if(!resCust.ok) throw new Error('Failed to load customer');
        const cust = await resCust.json();
        const jobsData = await resJobs.json();
        const resData = await resRes.json();
        setCustomer(cust);
        setJobs(jobsData.items || []);
        setReservations(resData || []);
        setEditing({ name: cust.name||'', phone: cust.phone||'', email: cust.email||'', street: cust.street||'', city: cust.city||'', zip: cust.zip||'' });
      }catch(e){ console.error(e) }finally{ setLoading(false) }
    }
    void load();
  },[id]);

  const save = async ()=>{
    try{
      setSaving(true);
      const res = await authFetch(`/api/v1/customers/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editing) });
      if(!res.ok) throw new Error('Save failed');
      const updated = await res.json();
      setCustomer(updated);
      setToast('Ulozeno');
      setTimeout(()=>setToast(null), 2500);
    }catch(e){ console.error(e) }finally{ setSaving(false) }
  }

  if(loading) return <div className="p-4">Loading...</div>
  if(!customer) return <div className="p-4">Not found</div>

  return (
    <div className="p-4">
      <button className="mb-4 border px-3 py-1" onClick={()=>router.push('/customers')}>Back</button>
      <h1 className="text-2xl mb-4">{customer.name}</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-xl border p-4 bg-white">
          <h2 className="font-semibold mb-2">Kontakt</h2>
          <label className="block text-sm">Jméno<input className="w-full border p-2 mt-1" value={editing.name} onChange={e=>setEditing({...editing, name: e.target.value})} /></label>
          <label className="block text-sm">Telefon<input className="w-full border p-2 mt-1" value={editing.phone} onChange={e=>setEditing({...editing, phone: e.target.value})} /></label>
          <label className="block text-sm">Email<input className="w-full border p-2 mt-1" value={editing.email} onChange={e=>setEditing({...editing, email: e.target.value})} /></label>
          <label className="block text-sm">Ulice<input className="w-full border p-2 mt-1" value={editing.street} onChange={e=>setEditing({...editing, street: e.target.value})} /></label>
          <label className="block text-sm">Město<input className="w-full border p-2 mt-1" value={editing.city} onChange={e=>setEditing({...editing, city: e.target.value})} /></label>
          <label className="block text-sm">PSČ<input className="w-full border p-2 mt-1" value={editing.zip} onChange={e=>setEditing({...editing, zip: e.target.value})} /></label>
          <div className="mt-3">
            <button className="border px-3 py-1" onClick={save} disabled={saving}>{saving? 'Saving...' : 'Save'}</button>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border p-4 bg-white">
            <h2 className="font-semibold">Historie zakázek</h2>
            {jobs.length===0 ? <div className="text-sm text-slate-500">Žádné zakázky</div> : (
              <ul className="mt-2 space-y-2">
                {jobs.map(j=> (
                  <li key={j.id} className="flex justify-between items-center">
                    <a className="text-sm text-blue-600" href={`/jobs/${j.id}`}>{j.job_number} · {j.status}</a>
                    <div className="text-xs text-slate-500">{j.installation_date ? new Date(j.installation_date).toLocaleString() : (j.created_at? new Date(j.created_at).toLocaleString() : '')}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border p-4 bg-white">
            <h2 className="font-semibold">Poslední rezervace</h2>
            {reservations.length===0 ? <div className="text-sm text-slate-500">Žádné rezervace</div> : (
              <ul className="mt-2 space-y-2">
                {reservations.map(r=> (
                  <li key={r.id} className="text-sm">{r.status} · {r.starts_at ? new Date(r.starts_at).toLocaleString() : r.created_at}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
      {toast ? <div className="fixed bottom-4 right-4 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">{toast}</div> : null}
    </div>
  )
}

