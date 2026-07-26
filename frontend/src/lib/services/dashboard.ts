import { authFetch } from '@/lib/auth';

export type DashboardJob = {
  id: number;
  job_number: string;
  status: string;
  priority: string;
  customer_name: string;
  technician?: string | null;
  installation_date?: string | null;
};

export type DashboardSummary = {
  status_counts: Record<string, number>;
  recent_jobs: DashboardJob[];
  overdue_jobs: DashboardJob[];
  today_installations: DashboardJob[];
  pipeline_counts: Record<string, number>;
};

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await authFetch('/api/v1/jobs/dashboard/summary');
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'Nepodarilo se nacist dashboard');
  }
  return response.json() as Promise<DashboardSummary>;
}
