import { NavLink } from "react-router-dom";
import { ROUTES } from "../../constants/routes";

const items = [
  ["home", "Home", ROUTES.STUDENT_HOME],
  ["receipt_long", "Orders", ROUTES.STUDENT_ORDERS],
  ["notifications", "Alerts", ROUTES.STUDENT_NOTIFS],
  ["person", "Profile", ROUTES.STUDENT_PROFILE],
];

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-1/2 z-50 flex h-20 w-full max-w-[430px] -translate-x-1/2 items-center justify-around border-t border-outline-variant bg-surface px-2 pb-safe">
      {items.map(([icon, label, to]) => (
        <NavLink key={to} to={to} className={({ isActive }) => `flex flex-col items-center text-xs ${isActive ? "text-primary-container" : "text-muted-text"}`}>
          <span className="material-symbols-outlined">{icon}</span><span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
