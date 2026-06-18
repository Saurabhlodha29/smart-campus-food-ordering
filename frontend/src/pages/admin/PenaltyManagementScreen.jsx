import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getPenalty, waivePenalty } from "../../api/penalties";
import { apiErrorMessage } from "../../api/client";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import { formatCurrency } from "../../utils/formatCurrency";

export default function PenaltyManagementScreen() {
  const [userId, setUserId] = useState(""); const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["penalty", userId], queryFn: () => getPenalty(userId), enabled: Boolean(userId) });
  const waive = useMutation({ mutationFn: waivePenalty, onSuccess: () => { toast.success("Penalty waived"); queryClient.invalidateQueries({ queryKey: ["penalty", userId] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <main className="min-h-dvh bg-background p-5"><h1 className="text-3xl font-bold">Penalty Management</h1><div className="mt-6 flex gap-3"><TextInput className="flex-1" placeholder="Student user ID" value={userId} onChange={(e) => setUserId(e.target.value)} /><Button onClick={() => query.refetch()}>Search</Button></div>{query.data && <div className="mt-6 rounded-3xl border border-border-glow bg-card-input p-6"><h2 className="text-xl font-bold">{query.data.fullName}</h2><p className="text-muted-text">{query.data.email}</p><p className="mt-5 text-3xl font-bold text-primary-container">{formatCurrency(query.data.pendingPenaltyAmount)}</p><Button className="mt-5" variant="outline" disabled={!query.data.pendingPenaltyAmount} onClick={() => waive.mutate(userId)}>Waive penalty</Button></div>}</main>;
}
