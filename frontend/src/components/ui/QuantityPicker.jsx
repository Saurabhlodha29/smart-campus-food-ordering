export default function QuantityPicker({ value, onDecrease, onIncrease }) {
  return (
    <div className="flex items-center gap-3 rounded-full bg-surface-container-high px-2 py-1">
      <button onClick={onDecrease} type="button" aria-label="Decrease quantity">−</button>
      <span className="min-w-5 text-center text-sm font-bold">{value}</span>
      <button onClick={onIncrease} type="button" aria-label="Increase quantity">+</button>
    </div>
  );
}
