export default function TopAppBar({ title, action }) {
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-outline-variant bg-surface px-5">
      <h1 className="text-xl font-bold text-on-surface">{title}</h1>{action}
    </header>
  );
}
