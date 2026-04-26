// lib/features/admin/admin_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/api/api_client.dart';
import '../../core/models/outlet_application_model.dart';
import '../../core/models/outlet_model.dart';

// ---------------------------------------------------------------------------
// OUTLET APPLICATIONS — PENDING
// ---------------------------------------------------------------------------

final pendingOutletAppsProvider =
    FutureProvider<List<OutletApplication>>((ref) async {
  final response =
      await ApiClient.dio.get('/api/outlet-applications/pending');
  return (response.data as List)
      .map((a) => OutletApplication.fromJson(a))
      .toList();
});

// ---------------------------------------------------------------------------
// OUTLET APPLICATIONS — ALL (history)
// ---------------------------------------------------------------------------

final allOutletAppsProvider =
    FutureProvider<List<OutletApplication>>((ref) async {
  final response =
      await ApiClient.dio.get('/api/outlet-applications/all');
  return (response.data as List)
      .map((a) => OutletApplication.fromJson(a))
      .toList();
});

// ---------------------------------------------------------------------------
// ALL OUTLETS ON CAMPUS (admin view — all statuses)
// ---------------------------------------------------------------------------

final campusOutletsAdminProvider =
    FutureProvider<List<Outlet>>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  final campusId = prefs.getString('campusId') ?? '';
  if (campusId.isEmpty) throw Exception('Campus ID not found.');
  final response =
      await ApiClient.dio.get('/api/outlets/campus/$campusId/all');
  return (response.data as List).map((o) => Outlet.fromJson(o)).toList();
});

// ---------------------------------------------------------------------------
// ADMIN ACTIONS NOTIFIER
// ---------------------------------------------------------------------------

class AdminNotifier extends Notifier<void> {
  @override
  void build() {}

  Future<void> approveOutletApp(int id, String tempPassword) async {
    await ApiClient.dio.patch(
      '/api/outlet-applications/$id/approve',
      data: {'temporaryPassword': tempPassword},
    );
    ref.invalidate(pendingOutletAppsProvider);
    ref.invalidate(allOutletAppsProvider);
  }

  Future<void> rejectOutletApp(int id, String reason) async {
    await ApiClient.dio.patch(
      '/api/outlet-applications/$id/reject',
      data: {'rejectionReason': reason},
    );
    ref.invalidate(pendingOutletAppsProvider);
    ref.invalidate(allOutletAppsProvider);
  }

  Future<void> suspendOutlet(int outletId) async {
    await ApiClient.dio.post('/api/outlets/$outletId/suspend');
    ref.invalidate(campusOutletsAdminProvider);
  }

  Future<void> reactivateOutlet(int outletId) async {
    await ApiClient.dio.post('/api/outlets/$outletId/reactivate');
    ref.invalidate(campusOutletsAdminProvider);
  }

  Future<Map<String, dynamic>> getPenaltyStatus(String userId) async {
    final response =
        await ApiClient.dio.get('/api/penalties/$userId/status');
    return response.data;
  }

  Future<void> waivePenalty(String userId) async {
    await ApiClient.dio.post('/api/penalties/$userId/waive');
  }
}

final adminProvider = NotifierProvider<AdminNotifier, void>(() {
  return AdminNotifier();
});