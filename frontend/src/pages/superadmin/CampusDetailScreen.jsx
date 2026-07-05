import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ShieldCheck, MapPin, Mail, Store } from "lucide-react";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import Button from "../../components/ui/Button";
import { DarkCard } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/Badge";
import EmptyState from "../../components/ui/EmptyState";
import { statusTone } from "../../utils/statusHelpers";

export default function CampusDetailScreen() {
  const { id } = useParams();
  const queryClient = useQueryClient();

  const campus = useQuery({ queryKey: ["campus", id], queryFn: async () => (await client.get(API.CAMPUS(id))).data });
  const users = useQuery({ queryKey: ["campus-users", id], queryFn: async () => (await client.get(API.CAMPUS_USERS(id))).data });
  const outlets = useQuery({ queryKey: ["campus-outlets-all", id], queryFn: async () => (await client.get(API.CAMPUS_OUTLETS_ALL(id))).data });

  const admin = (users.data || []).find((u) => u.role?.name === "ADMIN");

  const action = useMutation({
    mutationFn: () => client.post(campus.data?.status === "ACTIVE" ? API.CAMPUS_DEACTIVATE(id) : API.CAMPUS_REACTIVATE(id)),
    onSuccess: () => {
      toast.success("Campus status updated");
      queryClient.invalidateQueries({ queryKey: ["campus", id] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  return (
    <main className="min-h-dvh bg-background p-5 pb-28">
      <header className="rounded-3xl border border-border-glow bg-surface p-6">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-container">Campus</p>
        <h1 className="mt-2 text-3xl font-extrabold">{campus.data?.name || "—"}</h1>
        <p className="mt-1 flex items-center gap-2 text-sm text-muted-text">
          <MapPin size={14} /> {campus.data?.location} · @{campus.data?.emailDomain}
        </p>
        {campus.data && (
          <div className="mt-4 flex items-center gap-3">
            <StatusChip tone={statusTone(campus.data.status)}>{campus.data.status}</StatusChip>
            <Button variant="outline" onClick={() => action.mutate()} loading={action.isPending}>
              {campus.data.status === "ACTIVE" ? "Deactivate campus" : "Reactivate campus"}
            </Button>
          </div>
        )}
      </header>

      <section className="mt-6">
        <h2 className="text-lg font-bold">Campus Admin</h2>
        <div className="mt-3">
          {users.isLoading && <EmptyState loading title="Loading admin info" />}
          {!users.isLoading && !admin && <EmptyState title="No admin account found for this campus" />}
          {admin && (
            <DarkCard className="flex items-center gap-4 p-5">
              <div className="grid h-12 w-12 place-items-center rounded-full bg-primary-container/15 text-primary-container">
                <ShieldCheck size={22} />
              </div>
              <div>
                <p className="font-semibold">{admin.fullName}</p>
                <p className="flex items-center gap-1.5 text-sm text-muted-text">
                  <Mail size={13} /> {admin.email}
                </p>
              </div>
            </DarkCard>
          )}
        </div>
      </section>

      <section className="mt-6">
        <div className="flex items-center gap-2">
          <Store size={18} className="text-primary-container" />
          <h2 className="text-lg font-bold">Outlets on this campus</h2>
        </div>
        <div className="mt-3 space-y-3">
          {outlets.isLoading && <EmptyState loading title="Loading outlets" />}
          {outlets.isError && <EmptyState title="Could not load outlets" message={outlets.error?.message} />}
          {!outlets.isLoading && (outlets.data || []).length === 0 && (
            <EmptyState title="No outlets yet" message="Outlets will appear here once the admin approves an application." />
          )}
          {(outlets.data || []).map((outlet) => (
            <DarkCard className="flex items-center justify-between p-4" key={outlet.id}>
              <div>
                <p className="font-semibold">{outlet.name}</p>
                <p className="text-xs text-muted-text">Avg prep {outlet.avgPrepTime ?? "—"} min</p>
              </div>
              <StatusChip tone={statusTone(outlet.status)}>{outlet.status}</StatusChip>
            </DarkCard>
          ))}
        </div>
      </section>
    </main>
  );
}
