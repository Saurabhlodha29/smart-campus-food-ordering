import { NavLink, Outlet } from "react-router-dom";
import { ROUTES } from "../../constants/routes";

const links = [
  ["dashboard", "Dashboard", ROUTES.ADMIN_DASH],
  ["pending_actions", "Applications", ROUTES.ADMIN_APPS],
  ["storefront", "Outlets", ROUTES.ADMIN_OUTLETS],
  ["gavel", "Penalties", ROUTES.ADMIN_PENALTIES],
  ["notifications", "Alerts", ROUTES.ADMIN_NOTIFS],
];

export default function AdminLayout() {
  return (
    <div className="min-h-dvh bg-background md:grid md:grid-cols-[220px_1fr]">
      <aside className="fixed bottom-0 z-50 flex h-20 w-full items-center justify-around border-t border-outline-variant bg-surface md:sticky md:top-0 md:h-dvh md:flex-col md:justify-start md:gap-2 md:border-r md:border-t-0 md:p-5">
        <h2 className="mb-5 hidden text-xl font-bold text-primary-container md:block">Campus Admin</h2>
        {links.map(([icon, label, to]) => <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl p-3 ${isActive ? "bg-primary-container text-white" : "text-muted-text"}`}><span className="material-symbols-outlined">{icon}</span><span className="hidden md:inline">{label}</span></NavLink>)}
      </aside>
      <main className="pb-20 md:pb-0"><Outlet /></main>
    </div>
  );
}
