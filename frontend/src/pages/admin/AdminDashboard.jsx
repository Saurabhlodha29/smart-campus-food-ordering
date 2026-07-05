import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Store, CheckCircle2, Clock, Ban, ArrowRight, AlertTriangle } from "lucide-react";
import { getCampusOutlets } from "../../api/outlets";
import { getOutletApplications } from "../../api/applications";
import { useAuthStore } from "../../store/authStore";
import { DarkCard } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/Badge";
import { statusTone } from "../../utils/statusHelpers";
import { ROUTES } from "../../constants/routes";
import Spinner from "../../components/ui/Spinner";

export default function AdminDashboard() {
  const campusId = useAuthStore((s) => s.campusId);
  const campusName = useAuthStore((s) => s.campusName);

  const outlets = useQuery({
    queryKey: ["campus-outlets", campusId],
    queryFn: () => getCampusOutlets(campusId),
    enabled: Boolean(campusId),
  });
  const apps = useQuery({ queryKey: ["outlet-applications"], queryFn: getOutletApplications });

  const outletList = outlets.data || [];
  const pendingApps = apps.data || [];

  const stats = [
    { label: "Total Outlets", value: outletList.length, icon: Store, tone: "text-on-surface" },
    { label: "Active", value: outletList.filter((o) => o.status === "ACTIVE").length, icon: CheckCircle2, tone: "text-success" },
    { label: "Pending Apps", value: pendingApps.length, icon: Clock, tone: "text-accent-rating" },
    { label: "Suspended", value: outletList.filter((o) => o.status === "SUSPENDED").length, icon: Ban, tone: "text-error" },
  ];

  return (
    <main className="min-h-dvh bg-background p-5 pb-28">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-container">Campus Operations</p>
      <h1 className="mt-2 text-3xl font-extrabold">{campusName || "Admin Dashboard"}</h1>

      {pendingApps.length > 0 && (
        <Link
          to={ROUTES.ADMIN_APPS}
          className="mt-5 flex items-center gap-3 rounded-2xl border border-accent-rating/40 bg-accent-rating/10 p-4"
        >
          <AlertTriangle className="text-accent-rating" size={22} />
          <p className="flex-1 text-sm text-on-surface">
            <span className="font-semibold">
              {pendingApps.length} outlet application{pendingApps.length > 1 ? "s" : ""}
            </span>{" "}
            waiting for your review.
          </p>
          <ArrowRight className="text-accent-rating" size={18} />
        </Link>
      )}

      <section className="mt-6 grid grid-cols-2 gap-4">
        {stats.map(({ label, value, icon: Icon, tone }) => (
          <DarkCard className="p-5" key={label}>
            <Icon className={tone} size={22} />
            <p className="mt-3 text-xs uppercase tracking-wide text-muted-text">{label}</p>
            <p className="mt-1 text-3xl font-extrabold">{outlets.isLoading && label !== "Pending Apps" ? "—" : value}</p>
          </DarkCard>
        ))}
      </section>

      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Your Outlets</h2>
          <Link to={ROUTES.ADMIN_OUTLETS} className="text-sm font-semibold text-primary-container">Manage all →</Link>
        </div>

        <div className="mt-4 space-y-3">
          {outlets.isLoading && (
            <DarkCard className="grid place-items-center p-8"><Spinner /></DarkCard>
          )}
          {!outlets.isLoading && outletList.length === 0 && (
            <DarkCard className="p-6 text-center text-sm text-muted-text">
              No outlets yet. Approve an outlet application to get started.
            </DarkCard>
          )}
          {outletList.slice(0, 5).map((outlet) => (
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
