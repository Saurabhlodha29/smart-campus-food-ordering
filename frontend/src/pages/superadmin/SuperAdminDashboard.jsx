import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import { getAdminApplications, reviewAdminApplication } from "../../api/applications";
import { DarkCard } from "../../components/ui/Card";
import Button from "../../components/ui/Button";

export default function SuperAdminDashboard() {
  const queryClient = useQueryClient();
  const campuses = useQuery({ queryKey: ["campuses"], queryFn: async () => (await client.get(API.CAMPUSES)).data });
  const applications = useQuery({ queryKey: ["admin-applications"], queryFn: getAdminApplications });
  const review = useMutation({ mutationFn: reviewAdminApplication, onSuccess: () => { toast.success("Application reviewed"); queryClient.invalidateQueries({ queryKey: ["admin-applications"] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <main className="min-h-dvh bg-background p-5 pb-28"><header><p className="text-primary-container">PLATFORM CONTROL</p><h1 className="mt-2 text-3xl font-extrabold">Super Admin</h1></header><section className="mt-6 grid grid-cols-2 gap-4"><DarkCard className="p-5"><p className="text-xs text-muted-text">TOTAL CAMPUSES</p><p className="text-3xl font-extrabold">{campuses.data?.length || 0}</p></DarkCard><DarkCard className="p-5"><p className="text-xs text-muted-text">PENDING ADMINS</p><p className="text-3xl font-extrabold text-primary-container">{applications.data?.length || 0}</p></DarkCard></section><h2 className="mb-3 mt-8 text-xl font-bold">Admin applications</h2><div className="space-y-3">{applications.data?.map((app) => <DarkCard className="p-4" key={app.id}><h3 className="font-bold">{app.campusName}</h3><p className="text-sm text-secondary">{app.fullName} · {app.applicantEmail}</p><div className="mt-4 flex gap-2"><Button onClick={() => review.mutate({ id: app.id, approved: true, temporaryPassword: "Welcome@123", message: "Approved" })}>Approve</Button><Button variant="danger" onClick={() => review.mutate({ id: app.id, approved: false, message: "Rejected" })}>Reject</Button></div></DarkCard>)}</div></main>;
}
