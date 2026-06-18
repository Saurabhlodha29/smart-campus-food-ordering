import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";

export default function ProtectedRoute() {
  const token = useAuthStore((state) => state.token);
  const location = useLocation();
  return token ? <Outlet /> : <Navigate to={ROUTES.LOGIN} replace state={{ from: location }} />;
}
