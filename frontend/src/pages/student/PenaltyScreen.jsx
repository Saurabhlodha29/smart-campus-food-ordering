import { useQuery } from "@tanstack/react-query";
import { myPenalty } from "../../api/penalties";
import { formatCurrency } from "../../utils/formatCurrency";
import EmptyState from "../../components/ui/EmptyState";

export default function PenaltyScreen() {
  const query = useQuery({ queryKey: ["penalty"], queryFn: myPenalty });
  if (query.isLoading) return <EmptyState loading title="Checking penalties" />;
  const data = query.data;
  return <main className="min-h-dvh bg-background p-5"><h1 className="text-3xl font-bold">My Penalty</h1><div className="mt-6 rounded-3xl border border-border-glow bg-card-input p-6"><p className="text-muted-text">Outstanding amount</p><p className="mt-2 text-4xl font-extrabold text-primary-container">{formatCurrency(data?.pendingPenaltyAmount)}</p><p className="mt-4 text-sm text-secondary">No-shows: {data?.noShowCount || 0} · Account: {data?.accountStatus}</p></div></main>;
}
