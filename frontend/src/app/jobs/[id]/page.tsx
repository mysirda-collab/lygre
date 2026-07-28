"use client";
import { useState, useEffect } from "react";
import { fetchJob } from "../../../lib/api/jobs";
import { useRouter, useParams } from "next/navigation";
import { authFetch } from '@/lib/auth';

type JobType = {
  id: number;
  job_number: string;
  customer_name: string;
  company?: string;
  customer_id?: number;
  phone?: string;
  notes?: string;
  status?: string;
  created_at?: string;
  email?: string | null;
  street?: string | null;
  city?: string | null;
  zip?: string | null;
  priority?: string | null;
  installation_date?: string | null;
}

export default function JobDetailPage(){
  const params = useParams() as { id?: string };
  const id = params.id as string;
  const [job, setJob] = useState<JobType | null>(null);
  const [editing, setEditing] = useState<{phone:string, notes:string, email:string, street:string, city:string, zip:string, status:string, priority:string, installation_date:string}>({ phone: '', notes: '', email: '', street: '', city: '', zip: '', status: '', priority: '', installation_date: '' });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(()=>{
    fetchJob(id).then((data: JobType)=>{ 
      setJob(data); 
      setEditing({ 
        phone: data.phone||'', 
        notes: data.notes||'',
        email: data.email||'',
        street: data.street||'',
        city: data.city||'',
        zip: data.zip||'',
        status: data.status||'',
        priority: data.priority||'',
        installation_date: data.installation_date? data.installation_date.slice(0,10) : '',
      })
    }).catch(console.error)
  },[id]);

  if(!job) return <div className="p-4">Loading...</div>

  const save = async ()=>{
    try{
      const payload: Record<string, unknown> = {};
      if(!job) return;
      // basic validation
      if(editing.phone && !/^\+?[0-9 \-]{6,20}$/.test(editing.phone)) { setError('Neplatne cislo telefonu'); return }
      if(editing.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(editing.email)) { setError('Neplatny email'); return }
      setError(null);
      if(editing.phone !== (job.phone||'')) payload.phone = editing.phone;
      if(editing.notes !== (job.notes||'')) payload.notes = editing.notes;
      if(editing.email !== (job.email||'')) payload.email = editing.email;
      if(editing.street !== (job.street||'')) payload.street = editing.street;
      if(editing.city !== (job.city||'')) payload.city = editing.city;
      if(editing.zip !== (job.zip||'')) payload.zip = editing.zip;
      if(editing.status !== (job.status||'')) payload.status = editing.status;
      if(editing.priority !== (job.priority||'')) payload.priority = editing.priority;
      if(editing.installation_date !== (job.installation_date? job.installation_date.slice(0,10):'')) payload.installation_date = editing.installation_date || null;
      if(Object.keys(payload).length===0) return;
      setSaving(true);
      // prefer authFetch to include token
      const res = await authFetch(`/api/v1/jobs/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if(!res.ok) throw new Error('Ulozeni selhalo');
      // refresh
      const refreshed = await fetchJob(id);
      setJob(refreshed);
      setEditing({
        phone: refreshed.phone||'',
        notes: refreshed.notes||'',
        email: refreshed.email||'',
        street: refreshed.street||'',
        city: refreshed.city||'',
        zip: refreshed.zip||'',
        status: refreshed.status||'',
        priority: refreshed.priority||'',
        installation_date: refreshed.installation_date? refreshed.installation_date.slice(0,10) : ''
      });
      setToast('Zmeny ulozeny');
      setTimeout(()=>setToast(null), 3000);
    }catch(e){ console.error(e) }finally{ setSaving(false) }
  }

  return (
    <div className="p-4">
      {error ? <div className="mb-4 rounded border bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      <button className="mb-4 border px-3 py-1" onClick={()=>router.push('/jobs')}>Back</button>
      <h1 className="text-2xl mb-4">Job {job.job_number}</h1>
      <div className="mb-4">
        <h2 className="font-semibold">Customer</h2>
        {job.customer_id ? (
          <a href={`/customers/${job.customer_id}`} className="font-medium text-sky-600 hover:underline">{job.customer_name}</a>
        ) : (
          <div className="font-medium">{job.customer_name}</div>
        )}
        <div className="text-sm text-slate-600">{job.company}</div>
      </div>
      <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block">Phone</label>
          <input className="border p-2 w-full" value={editing.phone} onChange={e=>setEditing({...editing, phone: e.target.value})} />
        </div>
        <div>
          <label className="block">Email</label>
          <input className="border p-2 w-full" value={editing.email} onChange={e=>setEditing({...editing, email: e.target.value})} />
        </div>
        <div>
          <label className="block">Street</label>
          <input className="border p-2 w-full" value={editing.street} onChange={e=>setEditing({...editing, street: e.target.value})} />
        </div>
        <div>
          <label className="block">City</label>
          <input className="border p-2 w-full" value={editing.city} onChange={e=>setEditing({...editing, city: e.target.value})} />
        </div>
        <div>
          <label className="block">Installation date</label>
          <input type="date" className="border p-2 w-full" value={editing.installation_date} onChange={e=>setEditing({...editing, installation_date: e.target.value})} />
        </div>
        <div>
          <label className="block">Status</label>
          <select className="border p-2 w-full" value={editing.status} onChange={e=>setEditing({...editing, status: e.target.value})}>
            <option value="new">New</option>
            <option value="scheduled">Scheduled</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div>
          <label className="block">Priority</label>
          <select className="border p-2 w-full" value={editing.priority} onChange={e=>setEditing({...editing, priority: e.target.value})}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>
      <div className="mb-4">
        <h2 className="font-semibold">Details</h2>
        <div>Status: {job.status}</div>
        <div>Created: {job.created_at ? new Date(job.created_at).toLocaleString() : ''}</div>
      </div>
      <div className="mb-4">
        <label className="block">Notes</label>
        <textarea className="border p-2 w-full" value={editing.notes} onChange={e=>setEditing({...editing, notes: e.target.value})} />
      </div>
      <div>
        <button className="border px-3 py-1" onClick={save} disabled={saving}>{saving? 'Saving...' : 'Save'}</button>
      </div>
      {toast ? <div className="fixed bottom-4 right-4 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">{toast}</div> : null}
    </div>
  )
}
