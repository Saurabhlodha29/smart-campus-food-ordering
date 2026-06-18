import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { homeForRole } from "../../utils/roleRouting";

export default function RoleGuard({ roles }) {
  const role = useAuthStore((state) => state.role);
  return roles.includes(role) ? <Outlet /> : <Navigate to={homeForRole(role)} replace />;
}
