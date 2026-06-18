import { NavLink } from "react-router-dom";
import { ROUTES } from "../../constants/routes";

const ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard", to: ROUTES.MANAGER_DASH },
  { key: "menu", label: "Menu", icon: "restaurant_menu", to: ROUTES.MANAGER_MENU },
  { key: "slots", label: "Slots", icon: "schedule", to: ROUTES.MANAGER_SLOTS },
  { key: "ledger", label: "Ledger", icon: "account_balance_wallet", to: ROUTES.MANAGER_LEDGER },
  { key: "alerts", label: "Alerts", icon: "notifications", to: ROUTES.MANAGER_NOTIFS },
];

export default function ManagerBottomNav({ active }) {
  return (
    <nav className="fixed bottom-0 left-1/2 z-50 flex h-20 w-full max-w-[430px] -translate-x-1/2 items-center justify-around border-t border-outline-variant bg-surface px-1 pb-safe">
      {ITEMS.map((item) => {
        const selected = active === item.key;

        return (
          <NavLink
            className={`flex min-w-14 flex-col items-center justify-center transition-all active:scale-90 ${
              selected
                ? "text-primary after:mt-1 after:h-1 after:w-1 after:rounded-full after:bg-primary after:content-['']"
                : "text-muted-text hover:text-on-surface"
            }`}
            key={item.key}
            to={item.to}
          >
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: selected ? "'FILL' 1" : "'FILL' 0" }}
            >
              {item.icon}
            </span>
            <span className="font-label-sm text-label-sm">{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
