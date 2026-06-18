import { useQuery } from "@tanstack/react-query";
import { getCampusOutlets } from "../../api/outlets";
import { getOutletApplications } from "../../api/applications";
import { useAuthStore } from "../../store/authStore";
import { DarkCard } from "../../components/ui/Card";

export default function AdminDashboard() {
  const campusId = useAuthStore((s) => s.campusId);
  const outlets = useQuery({ queryKey: ["campus-outlets", campusId], queryFn: () => getCampusOutlets(campusId), enabled: Boolean(campusId) });
  const apps = useQuery({ queryKey: ["outlet-applications"], queryFn: getOutletApplications });
  const stats = [["Total Outlets", outlets.data?.length || 0],["Active", outlets.data?.filter((o) => o.status === "ACTIVE").length || 0],["Pending Apps", apps.data?.length || 0],["Suspended", outlets.data?.filter((o) => o.status === "SUSPENDED").length || 0]];
  return <main className="min-h-dvh bg-background p-5"><p className="text-primary-container">CAMPUS OPERATIONS</p><h1 className="mt-2 text-3xl font-extrabold">Admin Dashboard</h1><section className="mt-6 grid grid-cols-2 gap-4">{stats.map(([label,value]) => <DarkCard className="p-5" key={label}><p className="text-xs uppercase text-muted-text">{label}</p><p className="mt-2 text-3xl font-extrabold">{value}</p></DarkCard>)}</section></main>;
}
