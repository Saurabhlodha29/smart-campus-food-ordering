import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getOutletApplications, reviewOutletApplication } from "../../api/applications";
import { apiErrorMessage } from "../../api/client";
import ResourceListScreen from "../../components/screens/ResourceListScreen";
import Button from "../../components/ui/Button";

export default function OutletAppsScreen() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["outlet-applications"], queryFn: getOutletApplications });
  const review = useMutation({ mutationFn: reviewOutletApplication, onSuccess: () => { toast.success("Application reviewed"); queryClient.invalidateQueries({ queryKey: ["outlet-applications"] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <ResourceListScreen title="Outlet Applications" query={query} renderItem={(item) => <><h3 className="text-lg font-bold">{item.outletName}</h3><p className="text-sm text-secondary">{item.managerName} · {item.managerEmail}</p><p className="mt-2 text-xs text-muted-text">{item.outletDescription}</p><div className="mt-4 flex gap-3"><Button onClick={() => review.mutate({ id: item.id, approved: true, temporaryPassword: "Welcome@123", message: "Approved" })}>Approve</Button><Button variant="danger" onClick={() => review.mutate({ id: item.id, approved: false, message: "Application rejected" })}>Reject</Button></div></>} />;
}
