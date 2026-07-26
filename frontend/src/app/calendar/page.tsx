"use client";

import { useEffect, useMemo, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import timeGridPlugin from "@fullcalendar/timegrid";

import { authFetch } from "@/lib/auth";
import {
  TimeSlotRead,
  blockTimeSlot,
  createTimeSlot,
  listTimeSlots,
  updateTimeSlot,
} from "@/lib/services/calendarSlots";

type Technician = {
  id: number;
  full_name: string;
  email: string;
};

type Job = {
  id: number;
  job_number: string;
  customer_name: string;
  status: string;
};

type CalendarEventApi = {
  id: number;
  title: string;
  event_type: "installation" | "service" | "inspection";
  starts_at: string;
  ends_at: string;
  job_id: number;
  technician_id: number;
  notes?: string | null;
  job: {
    id: number;
    job_number: string;
    status: string;
    customer_name: string;
  };
  technician: {
    id: number;
    full_name: string;
    email: string;
  };
};

type CalendarListResponse = {
  items: CalendarEventApi[];
};

type JobListResponse = {
  items: Job[];
};

type EventForm = {
  title: string;
  event_type: "installation" | "service" | "inspection";
  starts_at: string;
  ends_at: string;
  job_id: string;
  technician_id: string;
  notes: string;
};

type SlotForm = {
  id?: number;
  start: string;
  end: string;
  capacity: number;
  technician: string;
  title: string;
  location: string;
  note: string;
  installation_type: string;
  enabled: boolean;
  blocked: boolean;
};

type DateSelectArg = {
  start: Date;
  end: Date;
};

type EventClickArg = {
  event: {
    extendedProps: {
      jobId?: number;
    };
  };
};

type EventMoveOrResizeArg = {
  event: {
    id: string;
    start: Date | null;
    end: Date | null;
  };
  revert: () => void;
};

type DatesSetArg = {
  start: Date;
  end: Date;
};

const emptyForm: EventForm = {
  title: "",
  event_type: "installation",
  starts_at: "",
  ends_at: "",
  job_id: "",
  technician_id: "",
  notes: "",
};

const emptySlotForm: SlotForm = {
  start: "",
  end: "",
  capacity: 1,
  technician: "",
  title: "",
  location: "",
  note: "",
  installation_type: "",
  enabled: true,
  blocked: false,
};

const calendarPlugins = [dayGridPlugin, timeGridPlugin, interactionPlugin] as unknown as never[];

function toInputDateTime(date: Date): string {
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return shifted.toISOString().slice(0, 16);
}

function statusColor(status: string): { bg: string; border: string } {
  if (status === "new") return { bg: "#dbeafe", border: "#60a5fa" };
  if (status === "scheduled") return { bg: "#fef3c7", border: "#f59e0b" };
  if (status === "done") return { bg: "#dcfce7", border: "#22c55e" };
  if (status === "cancelled") return { bg: "#ffe4e6", border: "#f43f5e" };
  return { bg: "#e2e8f0", border: "#94a3b8" };
}

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEventApi[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedTechnician, setSelectedTechnician] = useState("");

  const [slots, setSlots] = useState<TimeSlotRead[]>([]);
  const [slotForm, setSlotForm] = useState<SlotForm>(emptySlotForm);
  const [slotError, setSlotError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [rangeStart, setRangeStart] = useState<Date | null>(null);
  const [rangeEnd, setRangeEnd] = useState<Date | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<EventForm>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);

  const refreshSlots = async () => {
    const data = await listTimeSlots();
    setSlots(data);
  };

  const fetchEvents = async (start: Date, end: Date, technicianId?: string) => {
    const params = new URLSearchParams({
      start: start.toISOString(),
      end: end.toISOString(),
    });
    if (technicianId) {
      params.set("technician_id", technicianId);
    }

    const response = await authFetch(`/api/v1/calendar/events?${params.toString()}`);
    if (!response.ok) {
      throw new Error("Nepodarilo se nacist kalendar udalosti");
    }
    const data = (await response.json()) as CalendarListResponse;
    setEvents(data.items);
  };

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [techniciansRes, jobsRes, slotsData] = await Promise.all([
          authFetch("/api/v1/calendar/technicians"),
          authFetch("/api/v1/jobs?limit=200&sort_by=created_at&sort_desc=true"),
          listTimeSlots(),
        ]);

        if (!techniciansRes.ok) {
          throw new Error("Nepodarilo se nacist techniky");
        }
        if (!jobsRes.ok) {
          throw new Error("Nepodarilo se nacist zakazky");
        }

        const techniciansData = (await techniciansRes.json()) as Technician[];
        const jobsData = (await jobsRes.json()) as JobListResponse;

        setTechnicians(techniciansData);
        setJobs(jobsData.items);
        setSlots(slotsData);
        if (techniciansData.length > 0) {
          setSelectedTechnician((prev) => prev || String(techniciansData[0].id));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Neocekavana chyba kalendare");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (!rangeStart || !rangeEnd) return;
    const loadEvents = async () => {
      try {
        setLoading(true);
        setError(null);
        await fetchEvents(rangeStart, rangeEnd, selectedTechnician || undefined);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Neocekavana chyba pri nacitani udalosti");
      } finally {
        setLoading(false);
      }
    };
    void loadEvents();
  }, [rangeStart, rangeEnd, selectedTechnician]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const calendarEvents = useMemo(
    () =>
      events.map((event) => {
        const colors = statusColor(event.job.status);
        return {
          id: String(event.id),
          title: `${event.title} · ${event.job.job_number}`,
          start: event.starts_at,
          end: event.ends_at,
          backgroundColor: colors.bg,
          borderColor: colors.border,
          textColor: "#0f172a",
          extendedProps: {
            jobId: event.job_id,
            jobStatus: event.job.status,
            customer: event.job.customer_name,
            technicianName: event.technician.full_name,
          },
        };
      }),
    [events],
  );

  const openCreateModal = (selectedStart?: Date, selectedEnd?: Date) => {
    const now = new Date();
    const oneHourLater = new Date(now.getTime() + 60 * 60 * 1000);
    setForm({
      ...emptyForm,
      starts_at: toInputDateTime(selectedStart || now),
      ends_at: toInputDateTime(selectedEnd || oneHourLater),
      technician_id: selectedTechnician || technicians[0]?.id?.toString() || "",
      job_id: jobs[0]?.id?.toString() || "",
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleDateSelect = (arg: DateSelectArg) => {
    openCreateModal(arg.start, arg.end);
  };

  const handleEventClick = (arg: EventClickArg) => {
    const jobId = arg.event.extendedProps.jobId;
    if (jobId) {
      window.location.href = `/orders/${jobId}`;
    }
  };

  const handleEventMoveOrResize = async (arg: EventMoveOrResizeArg) => {
    const startsAt = arg.event.start;
    const endsAt = arg.event.end;
    if (!startsAt || !endsAt) {
      arg.revert();
      return;
    }

    const response = await authFetch(`/api/v1/calendar/events/${arg.event.id}/schedule`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        starts_at: startsAt.toISOString(),
        ends_at: endsAt.toISOString(),
      }),
    });

    if (!response.ok) {
      arg.revert();
      const data = await response.json().catch(() => ({}));
      setToast(data.detail || "Presun terminu selhal");
      return;
    }

    setToast("Termin byl upraven");
    if (rangeStart && rangeEnd) {
      await fetchEvents(rangeStart, rangeEnd, selectedTechnician || undefined);
    }
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);

    const response = await authFetch("/api/v1/calendar/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: form.title,
        event_type: form.event_type,
        starts_at: new Date(form.starts_at).toISOString(),
        ends_at: new Date(form.ends_at).toISOString(),
        job_id: Number(form.job_id),
        technician_id: Number(form.technician_id),
        notes: form.notes || null,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      setFormError(data.detail || "Vytvoreni udalosti selhalo");
      return;
    }

    setIsModalOpen(false);
    setToast("Udalost byla vytvorena");
    if (rangeStart && rangeEnd) {
      await fetchEvents(rangeStart, rangeEnd, selectedTechnician || undefined);
    }
  };

  const resetSlotForm = () => setSlotForm(emptySlotForm);

  const onSaveSlot = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      setSlotError(null);
      const payload = {
        start: new Date(slotForm.start).toISOString(),
        end: new Date(slotForm.end).toISOString(),
        capacity: Number(slotForm.capacity),
        enabled: slotForm.enabled,
        blocked: slotForm.blocked,
        technician: slotForm.technician || null,
        title: slotForm.title || null,
        location: slotForm.location || null,
        note: slotForm.note || null,
        installation_type: slotForm.installation_type || null,
      };

      if (slotForm.id) {
        await updateTimeSlot(slotForm.id, payload);
        setToast("Slot byl upraven");
      } else {
        await createTimeSlot(payload);
        setToast("Slot byl vytvoren");
      }

      await refreshSlots();
      resetSlotForm();
    } catch (err) {
      setSlotError(err instanceof Error ? err.message : "Ulozeni slotu selhalo");
    }
  };

  const onEditSlot = (slot: TimeSlotRead) => {
    setSlotForm({
      id: slot.id,
      start: toInputDateTime(new Date(slot.start)),
      end: toInputDateTime(new Date(slot.end)),
      capacity: slot.capacity,
      technician: slot.technician || "",
      title: slot.title || "",
      location: slot.location || "",
      note: slot.note || "",
      installation_type: slot.installation_type || "",
      enabled: slot.enabled,
      blocked: slot.blocked,
    });
    setSlotError(null);
  };

  const onToggleBlock = async (slot: TimeSlotRead) => {
    try {
      await blockTimeSlot(slot.id, !slot.blocked);
      await refreshSlots();
      setToast(slot.blocked ? "Slot byl odblokovan" : "Slot byl blokovan");
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Blokace slotu selhala");
    }
  };

  const techniciansEmpty = !loading && technicians.length === 0;

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Kalendar montazi</h1>
          <p className="mt-1 text-sm text-slate-500">Planovani montazi a sprava verejnych slotu rezervaci.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedTechnician}
            onChange={(e) => setSelectedTechnician(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Vsechny techniky</option>
            {technicians.map((technician) => (
              <option key={technician.id} value={technician.id}>
                {technician.full_name}
              </option>
            ))}
          </select>
          <button onClick={() => openCreateModal()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            Nova udalost
          </button>
        </div>
      </div>

      {error ? <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      {techniciansEmpty ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h2 className="text-lg font-semibold text-slate-800">Zatim nejsou dostupni technici</h2>
          <p className="mt-2 text-sm text-slate-500">Vytvorte uzivatele s roli worker, manager nebo admin.</p>
        </div>
      ) : loading && events.length === 0 ? (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          {Array.from({ length: 7 }).map((_, index) => (
            <div key={index} className="h-10 animate-pulse rounded bg-slate-100" />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          {events.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <h2 className="text-lg font-semibold text-slate-800">V tomto intervalu nejsou zadne udalosti</h2>
              <p className="mt-2 text-sm text-slate-500">Vyberte slot v kalendari nebo kliknete na Nova udalost.</p>
            </div>
          ) : null}
          <FullCalendar
            plugins={calendarPlugins}
            locale="cs"
            initialView="dayGridMonth"
            headerToolbar={{
              left: "prev,next today",
              center: "title",
              right: "dayGridMonth,timeGridWeek,timeGridDay",
            }}
            height="auto"
            selectable
            selectMirror
            editable
            dayMaxEvents
            events={calendarEvents}
            select={handleDateSelect}
            eventClick={handleEventClick}
            eventDrop={handleEventMoveOrResize}
            eventResize={handleEventMoveOrResize}
            datesSet={(arg: DatesSetArg) => {
              setRangeStart(arg.start);
              setRangeEnd(arg.end);
            }}
          />
        </div>
      )}

      <section className="mt-8 grid gap-6 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Sprava slotu rezervaci</h2>
          {slotError ? <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">{slotError}</div> : null}
          <form onSubmit={onSaveSlot} className="mt-4 grid gap-3">
            <div className="grid gap-3 md:grid-cols-2">
              <input
                type="datetime-local"
                value={slotForm.start}
                onChange={(event) => setSlotForm({ ...slotForm, start: event.target.value })}
                required
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="datetime-local"
                value={slotForm.end}
                onChange={(event) => setSlotForm({ ...slotForm, end: event.target.value })}
                required
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="number"
                min={1}
                value={slotForm.capacity}
                onChange={(event) => setSlotForm({ ...slotForm, capacity: Number(event.target.value) })}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                value={slotForm.technician}
                onChange={(event) => setSlotForm({ ...slotForm, technician: event.target.value })}
                placeholder="Technik"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                value={slotForm.title}
                onChange={(event) => setSlotForm({ ...slotForm, title: event.target.value })}
                placeholder="Nazev"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                value={slotForm.location}
                onChange={(event) => setSlotForm({ ...slotForm, location: event.target.value })}
                placeholder="Lokalita"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <textarea
              value={slotForm.note}
              onChange={(event) => setSlotForm({ ...slotForm, note: event.target.value })}
              placeholder="Poznamka"
              className="min-h-20 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={slotForm.installation_type}
                onChange={(event) => setSlotForm({ ...slotForm, installation_type: event.target.value })}
                placeholder="Typ instalace"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={slotForm.enabled}
                  onChange={(event) => setSlotForm({ ...slotForm, enabled: event.target.checked })}
                />
                Slot aktivni
              </label>
            </div>
            <div className="flex items-center gap-2">
              <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white" type="submit">
                {slotForm.id ? "Ulozit upravy" : "Vytvorit slot"}
              </button>
              {slotForm.id ? (
                <button
                  type="button"
                  onClick={resetSlotForm}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm"
                >
                  Zrusit editaci
                </button>
              ) : null}
            </div>
          </form>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Prehled slotu</h2>
          <div className="mt-4 max-h-[420px] space-y-2 overflow-auto">
            {slots.map((slot) => (
              <div key={slot.id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-semibold">{slot.title || "Rezervacni slot"}</div>
                  <div className="text-xs text-slate-500">
                    Obsazenost {slot.occupied_capacity}/{slot.capacity} · Volno {slot.remaining_capacity}
                  </div>
                </div>
                <div className="mt-1 text-xs text-slate-600">
                  {new Date(slot.start).toLocaleString("cs-CZ")} - {new Date(slot.end).toLocaleString("cs-CZ")}
                </div>
                <div className="mt-1 text-xs text-slate-500">{slot.location || "Bez lokality"}</div>
                <div className="mt-3 flex gap-2">
                  <button type="button" onClick={() => onEditSlot(slot)} className="rounded border border-slate-300 px-2 py-1 text-xs">
                    Editovat
                  </button>
                  <button
                    type="button"
                    onClick={() => onToggleBlock(slot)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs"
                  >
                    {slot.blocked ? "Odblokovat" : "Blokovat"}
                  </button>
                </div>
              </div>
            ))}
            {slots.length === 0 ? <div className="text-sm text-slate-500">Zadne sloty.</div> : null}
          </div>
        </div>
      </section>

      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Nova kalendarova udalost</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-sm text-slate-500">Zavrit</button>
            </div>

            {formError ? <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">{formError}</div> : null}

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium text-slate-700">
                  Nazev udalosti
                  <input
                    required
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Typ
                  <select
                    value={form.event_type}
                    onChange={(e) => setForm({ ...form, event_type: e.target.value as EventForm["event_type"] })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  >
                    <option value="installation">Montaz</option>
                    <option value="service">Servis</option>
                    <option value="inspection">Kontrola</option>
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Zacatek
                  <input
                    type="datetime-local"
                    required
                    value={form.starts_at}
                    onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Konec
                  <input
                    type="datetime-local"
                    required
                    value={form.ends_at}
                    onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Zakazka
                  <select
                    required
                    value={form.job_id}
                    onChange={(e) => setForm({ ...form, job_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  >
                    <option value="">Vyberte zakazku</option>
                    {jobs.map((job) => (
                      <option key={job.id} value={job.id}>
                        {job.job_number} · {job.customer_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Technik
                  <select
                    required
                    value={form.technician_id}
                    onChange={(e) => setForm({ ...form, technician_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                  >
                    <option value="">Vyberte technika</option>
                    {technicians.map((technician) => (
                      <option key={technician.id} value={technician.id}>
                        {technician.full_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block text-sm font-medium text-slate-700">
                Poznamka
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2"
                />
              </label>

              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">
                  Zrusit
                </button>
                <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">
                  Vytvorit udalost
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {toast ? <div className="fixed bottom-4 right-4 rounded-lg bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">{toast}</div> : null}
    </main>
  );
}
