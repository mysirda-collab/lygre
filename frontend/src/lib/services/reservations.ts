import { apiUrl } from '@/lib/api';

export type PublicSelectedSlot = {
  id: number;
  start: string;
  end: string;
  title: string | null;
  location: string | null;
  installation_type: string | null;
};

export type PublicReservationContext = {
  customer_name: string | null;
  job_number: string | null;
  reservation_status: string;
  token_expires_at: string | null;
  token_used: boolean;
  can_confirm: boolean;
  selected_slot: PublicSelectedSlot | null;
};

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

export type PublicAvailableSlotItem = {
  slot: TimeSlotRead;
  remaining_capacity: number;
};

export type PublicReservationConfirmResponse = {
  id: number;
  status: string;
  token_used: boolean;
  confirmation_sent_at: string | null;
  slot_id: number | null;
};

async function parseOrThrow<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  const data = await response.json().catch(() => ({}));
  const detail = typeof data?.detail === 'string' ? data.detail : 'Request failed';
  const err = new Error(detail) as Error & { status?: number };
  err.status = response.status;
  throw err;
}

export async function getPublicReservationContext(token: string): Promise<PublicReservationContext> {
  const response = await fetch(apiUrl(`/api/v1/reservations/public/${token}/context`), {
    method: 'GET',
    cache: 'no-store',
  });
  return parseOrThrow<PublicReservationContext>(response);
}

export async function getPublicReservationSlots(
  token: string,
  startIso: string,
  endIso: string,
  requiredCapacity: number = 1,
): Promise<PublicAvailableSlotItem[]> {
  const query = new URLSearchParams({
    start: startIso,
    end: endIso,
    required_capacity: String(requiredCapacity),
  });
  const response = await fetch(apiUrl(`/api/v1/reservations/public/${token}/available-slots?${query.toString()}`), {
    method: 'GET',
    cache: 'no-store',
  });
  const data = await parseOrThrow<{ items: PublicAvailableSlotItem[] }>(response);
  return data.items;
}

export async function confirmPublicReservation(token: string, slotId: number): Promise<PublicReservationConfirmResponse> {
  const response = await fetch(apiUrl('/api/v1/reservations/public/confirm'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, slot_id: slotId }),
  });
  return parseOrThrow<PublicReservationConfirmResponse>(response);
}
