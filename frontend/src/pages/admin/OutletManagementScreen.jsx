import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getCampusOutlets } from "../../api/outlets";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import { useAuthStore } from "../../store/authStore";
import ResourceListScreen from "../../components/screens/ResourceListScreen";
import Button from "../../components/ui/Button";
import { StatusChip } from "../../components/ui/Badge";
import { statusTone } from "../../utils/statusHelpers";

export default function OutletManagementScreen() {
  const campusId = useAuthStore((s) => s.campusId); const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["campus-outlets", campusId], queryFn: () => getCampusOutlets(campusId), enabled: Boolean(campusId) });
  const action = useMutation({ mutationFn: ({ id, status }) => client.post(status === "SUSPENDED" ? API.OUTLET_REACTIVATE(id) : API.OUTLET_SUSPEND(id)), onSuccess: () => { toast.success("Outlet status updated"); queryClient.invalidateQueries({ queryKey: ["campus-outlets"] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <ResourceListScreen title="Outlet Management" query={query} renderItem={(outlet) => <div className="flex items-center justify-between"><div><h3 className="font-bold">{outlet.name}</h3><StatusChip tone={statusTone(outlet.status)}>{outlet.status}</StatusChip></div><Button variant="outline" onClick={() => action.mutate(outlet)}>{outlet.status === "SUSPENDED" ? "Reactivate" : "Suspend"}</Button></div>} />;
}
