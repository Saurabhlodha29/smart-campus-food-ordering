import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import RoleGuard from "./components/auth/RoleGuard";
import StudentLayout from "./components/layout/StudentLayout";
import ManagerLayout from "./components/layout/ManagerLayout";
import AdminLayout from "./components/layout/AdminLayout";
import SuperAdminLayout from "./components/layout/SuperAdminLayout";
import { ROUTES } from "./constants/routes";
import { useAuthStore } from "./store/authStore";
import { homeForRole } from "./utils/roleRouting";

import LoginScreen from "./pages/auth/LoginScreen";
import RegisterScreen from "./pages/auth/RegisterScreen";
import ApplyAdminScreen from "./pages/auth/ApplyAdminScreen";
import ApplyOutletScreen from "./pages/auth/ApplyOutletScreen";
import HomeScreen from "./pages/student/HomeScreen";
import OutletDetailScreen from "./pages/student/OutletDetailScreen";
import CartScreen from "./pages/student/CartScreen";
import CheckoutScreen from "./pages/student/CheckoutScreen";
import OrderConfirmScreen from "./pages/student/OrderConfirmScreen";
import OrderTrackingScreen from "./pages/student/OrderTrackingScreen";
import MyOrdersScreen from "./pages/student/MyOrdersScreen";
import NotificationsScreen from "./pages/student/NotificationsScreen";
import ProfileScreen from "./pages/student/ProfileScreen";
import PenaltyScreen from "./pages/student/PenaltyScreen";
import OutletSetupScreen from "./pages/manager/OutletSetupScreen";
import ManagerDashboard from "./pages/manager/ManagerDashboard";
import MenuManagementScreen from "./pages/manager/MenuManagementScreen";
import SlotManagementScreen from "./pages/manager/SlotManagementScreen";
import AnalyticsScreen from "./pages/manager/AnalyticsScreen";
import LedgerScreen from "./pages/manager/LedgerScreen";
import ManagerNotifications from "./pages/manager/NotificationsScreen";
import AdminDashboard from "./pages/admin/AdminDashboard";
import OutletAppsScreen from "./pages/admin/OutletAppsScreen";
import OutletManagementScreen from "./pages/admin/OutletManagementScreen";
import PenaltyManagementScreen from "./pages/admin/PenaltyManagementScreen";
import AdminNotifications from "./pages/admin/NotificationsScreen";
import SuperAdminDashboard from "./pages/superadmin/SuperAdminDashboard";
import CampusListScreen from "./pages/superadmin/CampusListScreen";
import CampusDetailScreen from "./pages/superadmin/CampusDetailScreen";
import SuperAdminNotifications from "./pages/superadmin/NotificationsScreen";

function RootRedirect() {
  const token = useAuthStore((state) => state.token);
  const role = useAuthStore((state) => state.role);
  return <Navigate to={token ? homeForRole(role) : ROUTES.LOGIN} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path={ROUTES.LOGIN} element={<LoginScreen />} />
        <Route path={ROUTES.REGISTER} element={<RegisterScreen />} />
        <Route path={ROUTES.APPLY_ADMIN} element={<ApplyAdminScreen />} />
        <Route path={ROUTES.APPLY_OUTLET} element={<ApplyOutletScreen />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<RoleGuard roles={["STUDENT"]} />}>
            <Route element={<StudentLayout />}>
              <Route path={ROUTES.STUDENT_HOME} element={<HomeScreen />} />
              <Route path={ROUTES.STUDENT_OUTLET} element={<OutletDetailScreen />} />
              <Route path={ROUTES.STUDENT_CART} element={<CartScreen />} />
              <Route path={ROUTES.STUDENT_CHECKOUT} element={<CheckoutScreen />} />
              <Route path={ROUTES.STUDENT_CONFIRM} element={<OrderConfirmScreen />} />
              <Route path={ROUTES.STUDENT_TRACKING} element={<OrderTrackingScreen />} />
              <Route path={ROUTES.STUDENT_ORDERS} element={<MyOrdersScreen />} />
              <Route path={ROUTES.STUDENT_NOTIFS} element={<NotificationsScreen />} />
              <Route path={ROUTES.STUDENT_PROFILE} element={<ProfileScreen />} />
              <Route path={ROUTES.STUDENT_PENALTY} element={<PenaltyScreen />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["MANAGER"]} />}>
            <Route element={<ManagerLayout />}>
              <Route path={ROUTES.MANAGER_SETUP} element={<OutletSetupScreen />} />
              <Route path={ROUTES.MANAGER_DASH} element={<ManagerDashboard />} />
              <Route path={ROUTES.MANAGER_MENU} element={<MenuManagementScreen />} />
              <Route path={ROUTES.MANAGER_SLOTS} element={<SlotManagementScreen />} />
              <Route path={ROUTES.MANAGER_ANALYTICS} element={<AnalyticsScreen />} />
              <Route path={ROUTES.MANAGER_LEDGER} element={<LedgerScreen />} />
              <Route path={ROUTES.MANAGER_NOTIFS} element={<ManagerNotifications />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["ADMIN"]} />}>
            <Route element={<AdminLayout />}>
              <Route path={ROUTES.ADMIN_DASH} element={<AdminDashboard />} />
              <Route path={ROUTES.ADMIN_APPS} element={<OutletAppsScreen />} />
              <Route path={ROUTES.ADMIN_OUTLETS} element={<OutletManagementScreen />} />
              <Route path={ROUTES.ADMIN_PENALTIES} element={<PenaltyManagementScreen />} />
              <Route path={ROUTES.ADMIN_NOTIFS} element={<AdminNotifications />} />
            </Route>
          </Route>

          <Route element={<RoleGuard roles={["SUPERADMIN"]} />}>
            <Route element={<SuperAdminLayout />}>
              <Route path={ROUTES.SA_DASH} element={<SuperAdminDashboard />} />
              <Route path={ROUTES.SA_CAMPUSES} element={<CampusListScreen />} />
              <Route path={ROUTES.SA_CAMPUS_DETAIL} element={<CampusDetailScreen />} />
              <Route path={ROUTES.SA_NOTIFS} element={<SuperAdminNotifications />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}
