import { ROUTES } from "../constants/routes";

export const homeForRole = (role) => {
  const normalized = String(role || "").replace("ROLE_", "").toUpperCase();
  return {
    STUDENT: ROUTES.STUDENT_HOME,
    MANAGER: ROUTES.MANAGER_DASH,
    ADMIN: ROUTES.ADMIN_DASH,
    SUPERADMIN: ROUTES.SA_DASH,
  }[normalized] || ROUTES.LOGIN;
};
