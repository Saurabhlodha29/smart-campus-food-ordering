import Spinner from "./Spinner";

export default function EmptyState({ title = "Nothing here yet", message, loading = false }) {
  return (
    <div className="grid min-h-48 place-items-center rounded-2xl border border-border-glow bg-card-input p-6 text-center">
      <div>{loading && <Spinner className="mb-4" />}<h3 className="font-semibold">{title}</h3>{message && <p className="mt-2 text-sm text-muted-text">{message}</p>}</div>
    </div>
  );
}
