import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getMyOutlet, launchOutlet } from "../../api/outlets";
import { apiErrorMessage } from "../../api/client";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";

export default function OutletSetupScreen() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["my-outlet"], queryFn: getMyOutlet });
  const launch = useMutation({ mutationFn: () => launchOutlet(query.data.id), onSuccess: () => { toast.success("Outlet launched"); queryClient.invalidateQueries({ queryKey: ["my-outlet"] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  if (query.isLoading) return <EmptyState loading title="Loading outlet setup" />;
  return <main className="min-h-dvh bg-background p-5"><p className="text-primary-container">MANAGER ONBOARDING</p><h1 className="mt-2 text-3xl font-extrabold">Outlet Setup</h1><div className="mt-6 rounded-3xl border border-border-glow bg-card-input p-6"><h2 className="text-2xl font-bold">{query.data?.name}</h2><p className="mt-2 text-muted-text">Status: {query.data?.status}</p><p className="mt-5 text-sm text-secondary">Add at least one available menu item, confirm your operating details, then launch the outlet.</p><Button className="mt-6 w-full" loading={launch.isPending} disabled={query.data?.status !== "PENDING_LAUNCH"} onClick={() => launch.mutate()}>Launch outlet</Button></div></main>;
}
