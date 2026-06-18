import { Navigate } from "react-router-dom";
import { ROUTES } from "../../constants/routes";
export default function SplashScreen() { return <Navigate to={ROUTES.LOGIN} replace />; }
