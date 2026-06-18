import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import toast from "react-hot-toast";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import Button from "../../components/ui/Button";
import ResourceListScreen from "../../components/screens/ResourceListScreen";

export default function CampusDetailScreen() {
  const { id } = useParams(); const queryClient = useQueryClient();
  const campus = useQuery({ queryKey: ["campus", id], queryFn: async () => (await client.get(API.CAMPUS(id))).data });
  const outlets = useQuery({ queryKey: ["campus-outlets", id], queryFn: async () => (await client.get(API.CAMPUS_OUTLETS_ALL(id))).data });
  const action = useMutation({ mutationFn: () => client.post(campus.data?.status === "ACTIVE" ? API.CAMPUS_DEACTIVATE(id) : API.CAMPUS_REACTIVATE(id)), onSuccess: () => { toast.success("Campus status updated"); queryClient.invalidateQueries({ queryKey: ["campus", id] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <><header className="bg-surface p-5"><h1 className="text-3xl font-bold">{campus.data?.name || "Campus"}</h1><p className="text-muted-text">{campus.data?.location}</p><Button className="mt-4" variant="outline" onClick={() => action.mutate()}>{campus.data?.status === "ACTIVE" ? "Deactivate" : "Reactivate"}</Button></header><ResourceListScreen title="Campus Outlets" query={outlets} renderItem={(outlet) => <><h3 className="font-bold">{outlet.name}</h3><p className="text-sm text-muted-text">{outlet.status}</p></>} /></>;
}
