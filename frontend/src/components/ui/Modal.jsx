export function CenteredModal({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-black/70 p-5 backdrop-blur-sm" onClick={onClose}>
      <div className="max-h-[85dvh] w-full max-w-md overflow-auto rounded-3xl bg-surface p-5" onClick={(event) => event.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

export function BottomSheet({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-auto rounded-t-[32px] bg-surface p-5" onClick={(event) => event.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}
