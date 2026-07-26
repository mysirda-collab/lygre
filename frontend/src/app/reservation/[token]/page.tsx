"use client";

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import { SlotOptionCard } from '@/components/reservations/SlotOptionCard';
import {
  PublicAvailableSlotItem,
  PublicReservationContext,
  confirmPublicReservation,
  getPublicReservationContext,
  getPublicReservationSlots,
} from '@/lib/services/reservations';

type Props = {
  params: {
    token: string;
  };
};

export default function PublicReservationPage({ params }: Props) {
  const token = params.token;
  const router = useRouter();

  const [context, setContext] = useState<PublicReservationContext | null>(null);
  const [slots, setSlots] = useState<PublicAvailableSlotItem[]>([]);
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const range = useMemo(() => {
    const start = new Date();
    const end = new Date();
    end.setDate(end.getDate() + 30);
    return { start: start.toISOString(), end: end.toISOString() };
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const ctx = await getPublicReservationContext(token);
        setContext(ctx);

        if (!ctx.can_confirm) {
          if (ctx.token_used || ctx.reservation_status !== 'requested') {
            setSlots([]);
            return;
          }
          router.replace('/reservation/invalid');
          return;
        }

        const available = await getPublicReservationSlots(token, range.start, range.end, 1);
        setSlots(available);
      } catch (err) {
        const status = (err as Error & { status?: number }).status;
        if (status === 404 || status === 422) {
          router.replace('/reservation/invalid');
          return;
        }
        setError(err instanceof Error ? err.message : 'Nepodarilo se nacist rezervaci');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [token, range.start, range.end, router]);

  const submit = async () => {
    if (!selectedSlotId) return;
    try {
      setSubmitting(true);
      setError(null);
      await confirmPublicReservation(token, selectedSlotId);
      router.replace(`/reservation/success?token=${encodeURIComponent(token)}`);
    } catch (err) {
      const status = (err as Error & { status?: number }).status;
      if (status === 404 || status === 422) {
        router.replace('/reservation/invalid');
        return;
      }
      setError(err instanceof Error ? err.message : 'Potvrzeni rezervace selhalo');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <main className="min-h-screen bg-slate-50 p-6 text-sm text-slate-500">Nacitam rezervaci...</main>;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-3xl space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">Vyber terminu montaze</h1>
          <p className="mt-2 text-sm text-slate-600">Zakazka: {context?.job_number || '-'}</p>
          <p className="text-sm text-slate-600">Zakaznik: {context?.customer_name || '-'}</p>
          <p className="text-sm text-slate-600">Stav rezervace: {context?.reservation_status || '-'}</p>
        </section>

        {context?.selected_slot ? (
          <section className="rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Rezervace je jiz potvrzena</h2>
            <p className="mt-2 text-sm text-slate-600">
              Termin: {new Date(context.selected_slot.start).toLocaleString('cs-CZ')} -{' '}
              {new Date(context.selected_slot.end).toLocaleString('cs-CZ')}
            </p>
          </section>
        ) : null}

        {context?.can_confirm ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Dostupne terminy</h2>
            <div className="mt-4 space-y-3">
              {slots.map((item) => (
                <SlotOptionCard
                  key={item.slot.id}
                  item={item}
                  checked={selectedSlotId === item.slot.id}
                  onSelect={(slotId) => setSelectedSlotId(slotId)}
                />
              ))}
              {slots.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                  V aktualnim intervalu nejsou volne terminy. Kontaktujte prosim dispecink.
                </div>
              ) : null}
            </div>
            {error ? <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={submit}
                disabled={!selectedSlotId || submitting}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                {submitting ? 'Potvrzuji...' : 'Potvrdit rezervaci'}
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
