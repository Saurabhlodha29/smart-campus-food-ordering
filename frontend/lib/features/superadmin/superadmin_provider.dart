// lib/features/superadmin/superadmin_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/models/admin_application_model.dart';

// Fetches only PENDING applications (main review tab)
final pendingAdminAppsProvider = FutureProvider<List<AdminApplication>>((ref) async {
  final response = await ApiClient.dio.get('/api/admin-applications');
  return (response.data as List)
      .map((app) => AdminApplication.fromJson(app))
      .toList();
});

// Fetches ALL applications regardless of status (history tab)
// BUG FIX: this provider was missing — the history tab had no data source
final allAdminAppsProvider = FutureProvider<List<AdminApplication>>((ref) async {
  final response = await ApiClient.dio.get('/api/admin-applications/all');
  return (response.data as List)
      .map((app) => AdminApplication.fromJson(app))
      .toList();
});

// Handles approve / reject actions
class SuperAdminNotifier extends Notifier<void> {
  @override
  void build() {}

  Future<void> approveApplication(int id, String tempPassword) async {
    await ApiClient.dio.patch(
      '/api/admin-applications/$id/approve',
      data: {'temporaryPassword': tempPassword},
    );
    // Refresh both lists after action
    ref.invalidate(pendingAdminAppsProvider);
    ref.invalidate(allAdminAppsProvider);
  }

  Future<void> rejectApplication(int id, String reason) async {
    await ApiClient.dio.patch(
      '/api/admin-applications/$id/reject',
      data: {'rejectionReason': reason},
    );
    ref.invalidate(pendingAdminAppsProvider);
    ref.invalidate(allAdminAppsProvider);
  }
}

final superAdminProvider = NotifierProvider<SuperAdminNotifier, void>(() {
  return SuperAdminNotifier();
});