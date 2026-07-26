import { authFetch } from '@/lib/auth';

export type TimeSlotRead = {
  id: number;
  start: string;
  end: string;
  capacity: number;
  enabled: boolean;
  blocked: boolean;
  technician: string | null;
  title: string | null;
  location: string | null;
  note: string | null;
  installation_type: string | null;
  occupied_capacity: number;
  remaining_capacity: number;
  created_at: string;
  updated_at: string;
};

export type TimeSlotCreatePayload = {
  start: string;
  end: string;
  capacity: number;
  enabled: boolean;
  blocked: boolean;
  technician: string | null;
  title: string | null;
  location: string | null;
  note: string | null;
  installation_type: string | null;
};

export type TimeSlotUpdatePayload = Partial<TimeSlotCreatePayload>;

async function parseOrThrow<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  const data = await response.json().catch(() => ({}));
  throw new Error(typeof data?.detail === 'string' ? data.detail : 'Request failed');
}

export async function listTimeSlots(): Promise<TimeSlotRead[]> {
  const response = await authFetch('/api/v1/calendar/slots?include_blocked=true');
  const data = await parseOrThrow<{ items: TimeSlotRead[] }>(response);
  return data.items;
}

export async function createTimeSlot(payload: TimeSlotCreatePayload): Promise<TimeSlotRead> {
  const response = await authFetch('/api/v1/calendar/slots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseOrThrow<TimeSlotRead>(response);
}

export async function updateTimeSlot(slotId: number, payload: TimeSlotUpdatePayload): Promise<TimeSlotRead> {
  const response = await authFetch(`/api/v1/calendar/slots/${slotId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseOrThrow<TimeSlotRead>(response);
}

export async function blockTimeSlot(slotId: number, blocked: boolean): Promise<TimeSlotRead> {
  const response = await authFetch(`/api/v1/calendar/slots/${slotId}/block`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blocked, disable: true }),
  });
  return parseOrThrow<TimeSlotRead>(response);
}
