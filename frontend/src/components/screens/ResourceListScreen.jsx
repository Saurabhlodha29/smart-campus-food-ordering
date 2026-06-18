import EmptyState from "../ui/EmptyState";
import { DarkCard } from "../ui/Card";

export default function ResourceListScreen({ title, query, renderItem }) {
  return <main className="min-h-dvh bg-background p-5 pb-28"><h1 className="mb-6 text-3xl font-bold">{title}</h1>{query.isLoading ? <EmptyState loading title={`Loading ${title.toLowerCase()}`} /> : query.isError ? <EmptyState title="Could not load data" message={query.error?.message} /> : query.data?.length ? <div className="space-y-3">{query.data.map((item, index) => <DarkCard className="p-4" key={item.id ?? index}>{renderItem ? renderItem(item) : <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(item, null, 2)}</pre>}</DarkCard>)}</div> : <EmptyState title={`No ${title.toLowerCase()} yet`} />}</main>;
}
