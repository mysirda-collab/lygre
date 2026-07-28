"use client";
import { useState, useEffect } from "react";
import { fetchJobs } from "../../lib/api/jobs";
import { useRouter, useSearchParams } from "next/navigation";

type JobType = {
  id: number;
  job_number: string;
  customer_name?: string;
  phone?: string;
  status?: string;
  created_at?: string;
  installation_date?: string | null;
}

export default function JobsPage() {
  const [items, setItems] = useState<Array<JobType>>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sortBy] = useState<string>('created_at');
  const [sortDesc, setSortDesc] = useState<boolean>(true);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const skip = (page - 1) * pageSize;
    fetchJobs({ skip, limit: pageSize, search, sort_by: sortBy, sort_desc: String(sortDesc), status: statusFilter }).then(data => {
      setItems(data.items || []);
      setTotal(data.total || 0);
    }).catch(console.error);
  }, [page, pageSize, search, sortBy, sortDesc, statusFilter]);

  useEffect(()=>{ setPage(1) }, [search, statusFilter, sortBy, sortDesc]);

  useEffect(()=>{
    const s = searchParams.get('status') || '';
    if(s && s !== statusFilter) setStatusFilter(s);
  },[searchParams]);

  return (
    <div className="p-4">
      <h1 className="text-2xl mb-4">Jobs</h1>
      <div className="mb-4">
        <div className="flex gap-2">
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search job number / name / phone" className="border p-2 w-full" />
          <select value={statusFilter} onChange={e=>{ setStatusFilter(e.target.value); const params = new URLSearchParams(window.location.search); if(e.target.value) params.set('status', e.target.value); else params.delete('status'); router.push(`/jobs?${params.toString()}`) }} className="border p-2">
            <option value="">All</option>
            <option value="new">New</option>
            <option value="scheduled">Scheduled</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button onClick={()=>{ setSortDesc(s=>!s) }} className="border p-2">Sort {sortDesc? '↓':'↑'}</button>
        </div>
      </div>
      <table className="w-full border-collapse border">
        <thead>
          <tr>
            <th className="border p-2">Job Number</th>
            <th className="border p-2">Customer</th>
            <th className="border p-2">Phone</th>
            <th className="border p-2">Status</th>
            <th className="border p-2">Created At</th>
            <th className="border p-2">Installation</th>
          </tr>
        </thead>
        <tbody>
          {items.map((j: JobType) => (
            <tr key={j.id} className="cursor-pointer hover:bg-gray-100" onClick={()=>router.push(`/jobs/${j.id}`)}>
              <td className="border p-2">{j.job_number}</td>
              <td className="border p-2">{j.customer_name}</td>
              <td className="border p-2">{j.phone}</td>
              <td className="border p-2">
                <span className={`inline-block px-2 py-1 rounded text-xs ${j.status==='new'? 'bg-blue-100 text-blue-800' : j.status==='scheduled'? 'bg-yellow-100 text-yellow-800' : j.status==='done'? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>{j.status}</span>
              </td>
              <td className="border p-2">{j.created_at ? new Date(j.created_at).toLocaleString() : ''}</td>
              <td className="border p-2">{j.installation_date ? new Date(j.installation_date).toLocaleDateString() : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4">
        <button disabled={page<=1} onClick={()=>setPage(p=>Math.max(1,p-1))} className="mr-2 border px-3 py-1">Prev</button>
        <span>Page {page} / {Math.ceil(total/pageSize) || 1}</span>
        <button disabled={page>=Math.ceil(total/pageSize) || false} onClick={()=>setPage(p=>p+1)} className="ml-2 border px-3 py-1">Next</button>
      </div>
    </div>
  )
}
