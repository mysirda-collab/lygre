import { authFetch } from '@/lib/auth';

export async function fetchJobs({ skip = 0, limit = 20, search = '', sort_by = 'created_at', sort_desc = 'true', status = '', customer_id }: { skip?: number; limit?: number; search?: string; sort_by?: string; sort_desc?: string; status?: string; customer_id?: string | number } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit), search, sort_by, sort_desc });
  if (status) params.set('status', String(status));
  if (customer_id) params.set('customer_id', String(customer_id));
  const res = await authFetch(`/api/v1/jobs?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function fetchJob(id: string | number) {
  const res = await authFetch(`/api/v1/jobs/${id}`);
  if (!res.ok) throw new Error('Failed to fetch job');
  return res.json();
}

export async function patchJob(id: string | number, payload: Record<string, unknown>) {
  const res = await authFetch(`/api/v1/jobs/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error('Failed to patch job');
  return res.json();
}
