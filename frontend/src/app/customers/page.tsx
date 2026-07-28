"use client";
import { useState } from 'react';
type Customer = { id: number; name: string; phone?: string | null; email?: string | null }
import { useRouter } from 'next/navigation';
import { authFetch } from '@/lib/auth';

export default function CustomersPage() {
  const [q, setQ] = useState('');
  const [items, setItems] = useState<Customer[]>([]);
  const router = useRouter();

  const search = async ()=>{
    if(!q) return setItems([]);
    const res = await authFetch(`/api/v1/customers?q=${encodeURIComponent(q)}`);
    if(!res.ok) return;
    const data = await res.json();
    setItems(data || []);
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Zákazníci</h1>
      <div className="mt-4 mb-4 flex gap-2">
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Hledat jméno nebo číslo" className="border p-2" />
        <button onClick={search} className="border px-3 py-1">Hledat</button>
      </div>
      <div>
        {items.length===0 ? <div className="text-sm text-slate-500">Žádné výsledky</div> : (
          <table className="w-full border-collapse border">
            <thead><tr><th className="border p-2">Jméno</th><th className="border p-2">Telefon</th><th className="border p-2">Email</th></tr></thead>
            <tbody>
              {items.map(c=> (
                <tr key={c.id} className="cursor-pointer hover:bg-gray-100" onClick={()=>router.push(`/customers/${c.id}`)}>
                  <td className="border p-2">{c.name}</td>
                  <td className="border p-2">{c.phone || ''}</td>
                  <td className="border p-2">{c.email || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  )
}
