import { PublicAvailableSlotItem } from '@/lib/services/reservations';

type Props = {
  item: PublicAvailableSlotItem;
  checked: boolean;
  onSelect: (slotId: number) => void;
};

export function SlotOptionCard({ item, checked, onSelect }: Props) {
  const start = new Date(item.slot.start);
  const end = new Date(item.slot.end);
  const fmt = new Intl.DateTimeFormat('cs-CZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <button
      type="button"
      onClick={() => onSelect(item.slot.id)}
      className={`w-full rounded-xl border p-4 text-left transition ${
        checked ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white hover:border-slate-400'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">{item.slot.title || 'Montazni termin'}</div>
        <div className="text-xs opacity-80">Volna kapacita: {item.remaining_capacity}</div>
      </div>
      <div className="mt-2 text-sm">
        {fmt.format(start)} - {fmt.format(end)}
      </div>
      <div className="mt-1 text-xs opacity-80">{item.slot.location || 'Lokalita bude upresnena'}</div>
    </button>
  );
}
