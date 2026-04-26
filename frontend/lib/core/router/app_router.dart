// lib/core/router/app_router.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../storage/secure_storage.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/auth/admin_application_screen.dart';
import '../../features/auth/outlet_application_screen.dart';
import '../../features/superadmin/superadmin_dashboard_screen.dart';
import '../../features/admin/admin_dashboard_screen.dart';
import '../../features/admin/outlet_app_review_screen.dart';
import '../../features/admin/outlet_app_history_screen.dart';
import '../../features/admin/outlet_management_screen.dart';
import '../../features/admin/penalty_management_screen.dart';
import '../../features/student/student_home_screen.dart';
import '../../features/student/outlet_detail_screen.dart';
import '../../features/student/cart_screen.dart';
import '../../features/student/order_confirmation_screen.dart';
import '../../features/student/my_orders_screen.dart';
import '../../features/student/penalty_screen.dart';
import '../../features/student/profile_screen.dart';
import '../../features/manager/manager_dashboard_screen.dart';
import '../../features/manager/outlet_setup_screen.dart';
import '../../features/manager/menu_management_screen.dart';
import '../../features/manager/slot_management_screen.dart';
import '../../features/notifications/notifications_screen.dart';
import '../../features/student/student_main_scaffold.dart';
import '../../core/models/order_model.dart';
import 'package:flutter/widgets.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<NavigatorState> _studentShellNavigatorKey = GlobalKey<NavigatorState>();

final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/login',

  redirect: (context, state) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final role = prefs.getString('role');
      final token = await StorageService.getToken();

      final isLoggedIn = token != null && role != null;
      final isAtLogin = state.matchedLocation == '/login';

      final isOnPublicRoute = [
        '/login', '/register', '/apply-admin', '/apply-outlet',
      ].contains(state.matchedLocation);

      if (!isLoggedIn && !isOnPublicRoute) return '/login';

      if (isLoggedIn && isAtLogin) {
        return switch (role) {
          'SUPERADMIN' => '/superadmin/dashboard',
          'ADMIN'      => '/admin/dashboard',
          'MANAGER'    => '/manager/dashboard',
          'STUDENT'    => '/student/home',
          _            => '/login',
        };
      }
      return null;
    } catch (e) {
      debugPrint('Router Error: $e');
      return '/login';
    }
  },

  routes: [
    // ── PUBLIC ──────────────────────────────────────────────────────────────
    GoRoute(path: '/login',        builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/register',     builder: (_, __) => const RegisterScreen()),
    GoRoute(path: '/apply-admin',  builder: (_, __) => const AdminApplicationScreen()),
    GoRoute(path: '/apply-outlet', builder: (_, __) => const OutletApplicationScreen()),

    // ── SUPERADMIN ───────────────────────────────────────────────────────────
    GoRoute(path: '/superadmin/dashboard',
        builder: (_, __) => const SuperAdminDashboardScreen()),
    GoRoute(path: '/superadmin/notifications',
        builder: (_, __) => const NotificationsScreen()),

    // ── ADMIN ────────────────────────────────────────────────────────────────
    GoRoute(path: '/admin/dashboard',
        builder: (_, __) => const AdminDashboardScreen()),
    GoRoute(path: '/admin/outlet-apps',
        builder: (_, __) => const OutletAppReviewScreen()),
    GoRoute(path: '/admin/outlet-history',
        builder: (_, __) => const OutletAppHistoryScreen()),
    GoRoute(path: '/admin/outlets',
        builder: (_, __) => const OutletManagementScreen()),
    GoRoute(path: '/admin/penalties',
        builder: (_, __) => const PenaltyManagementScreen()),
    GoRoute(path: '/admin/notifications',
        builder: (_, __) => const NotificationsScreen()),

    // ── STUDENT ──────────────────────────────────────────────────────────────
    ShellRoute(
      navigatorKey: _studentShellNavigatorKey,
      builder: (context, state, child) => StudentMainScaffold(child: child),
      routes: [
        GoRoute(
          path: '/student/home',
          builder: (_, __) => const StudentHomeScreen(),
        ),
        GoRoute(
          path: '/student/outlet/:id',
          builder: (_, state) =>
              OutletDetailScreen(outletId: state.pathParameters['id']!),
        ),
        GoRoute(
          path: '/student/cart',
          builder: (_, __) => const CartScreen(),
        ),
        GoRoute(
          path: '/student/order-confirm',
          builder: (_, state) =>
              OrderConfirmationScreen(order: state.extra as Order),
        ),
        GoRoute(
          path: '/student/orders',
          builder: (_, __) => const MyOrdersScreen(),
        ),
        GoRoute(
          path: '/student/notifications',
          builder: (_, __) => const NotificationsScreen(),
        ),
        GoRoute(
          path: '/student/penalty',
          builder: (_, __) => const PenaltyScreen(),
        ),
        GoRoute(
          path: '/student/profile',
          builder: (_, __) => const ProfileScreen(),
        ),
      ],
    ),

    // ── MANAGER ──────────────────────────────────────────────────────────────
    GoRoute(path: '/manager/setup',
        builder: (_, __) => const OutletSetupScreen()),
    GoRoute(path: '/manager/dashboard',
        builder: (_, __) => const ManagerDashboardScreen()),
    GoRoute(path: '/manager/menu',
        builder: (_, __) => const MenuManagementScreen()),
    GoRoute(path: '/manager/slots',
        builder: (_, __) => const SlotManagementScreen()),
    GoRoute(path: '/manager/notifications',
        builder: (_, __) => const NotificationsScreen()),
  ],
);