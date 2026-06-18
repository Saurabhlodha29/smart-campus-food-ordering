import { NavLink, Outlet } from "react-router-dom";
import { ROUTES } from "../../constants/routes";

export default function SuperAdminLayout() {
  return (
    <div className="min-h-dvh bg-background pb-20">
      <Outlet />
      <nav className="fixed bottom-0 left-1/2 z-50 flex h-20 w-full max-w-[430px] -translate-x-1/2 justify-around border-t border-outline-variant bg-surface">
        <NavLink to={ROUTES.SA_DASH} className="grid place-items-center text-primary-container">Dashboard</NavLink>
        <NavLink to={ROUTES.SA_CAMPUSES} className="grid place-items-center text-muted-text">Campuses</NavLink>
        <NavLink to={ROUTES.SA_NOTIFS} className="grid place-items-center text-muted-text">Alerts</NavLink>
      </nav>
    </div>
  );
}
