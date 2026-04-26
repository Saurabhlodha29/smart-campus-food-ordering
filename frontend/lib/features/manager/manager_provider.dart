// lib/features/manager/manager_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/api/api_client.dart';
import '../../core/models/outlet_model.dart';
import '../../core/models/menu_item_model.dart';
import '../../core/models/pickup_slot_model.dart';
import '../../core/models/order_model.dart';

// ---------------------------------------------------------------------------
// MY OUTLET
// ---------------------------------------------------------------------------

final myOutletProvider = FutureProvider<Outlet>((ref) async {
  final response = await ApiClient.dio.get('/api/outlets/mine');
  return Outlet.fromJson(response.data);
});

// ---------------------------------------------------------------------------
// MENU ITEMS (manager view — includes out of stock)
// ---------------------------------------------------------------------------

final managerMenuProvider = FutureProvider<List<MenuItem>>((ref) async {
  final outlet = await ref.watch(myOutletProvider.future);
  final response =
      await ApiClient.dio.get('/api/menu-items/all?outletId=${outlet.id}');
  return (response.data as List).map((m) => MenuItem.fromJson(m)).toList();
});

// ---------------------------------------------------------------------------
// SLOTS
// ---------------------------------------------------------------------------

final managerSlotsProvider = FutureProvider<List<PickupSlot>>((ref) async {
  final response = await ApiClient.dio.get('/api/slots');
  return (response.data as List).map((s) => PickupSlot.fromJson(s)).toList();
});

// ---------------------------------------------------------------------------
// ORDERS (manager sees all orders for their outlet)
// ---------------------------------------------------------------------------

final managerOrdersProvider = FutureProvider<List<Order>>((ref) async {
  final response = await ApiClient.dio.get('/api/orders');
  return (response.data as List).map((o) => Order.fromJson(o)).toList();
});

// ---------------------------------------------------------------------------
// MANAGER ACTIONS NOTIFIER
// ---------------------------------------------------------------------------

class ManagerNotifier extends Notifier<void> {
  @override
  void build() {}

  // Update order status: PLACED→PREPARING→READY→PICKED
  Future<void> updateOrderStatus(int orderId, String newStatus) async {
    await ApiClient.dio.patch('/api/orders/$orderId/status', data: {
      'status': newStatus,
    });
    ref.invalidate(managerOrdersProvider);
  }

  // Add a menu item
  Future<void> addMenuItem(Map<String, dynamic> data) async {
    final outlet = await ref.read(myOutletProvider.future);
    await ApiClient.dio.post('/api/menu-items', data: {
      ...data,
      'outletId': outlet.id,
    });
    ref.invalidate(managerMenuProvider);
  }

  // Edit a menu item
  Future<void> editMenuItem(int id, Map<String, dynamic> data) async {
    await ApiClient.dio.patch('/api/menu-items/$id', data: data);
    ref.invalidate(managerMenuProvider);
  }

  // Delete a menu item
  Future<void> deleteMenuItem(int id) async {
    await ApiClient.dio.delete('/api/menu-items/$id');
    ref.invalidate(managerMenuProvider);
  }

  // Toggle availability
  Future<void> toggleAvailability(int id, bool available) async {
    await ApiClient.dio.patch('/api/menu-items/$id/availability', data: {
      'available': available,
    });
    ref.invalidate(managerMenuProvider);
  }

  // Launch outlet (PENDING_LAUNCH → ACTIVE)
  Future<void> launchOutlet(int outletId) async {
    await ApiClient.dio.post('/api/outlets/$outletId/launch');
    ref.invalidate(myOutletProvider);
  }

  // Create a pickup slot
  Future<void> createSlot(Map<String, dynamic> data) async {
    final outlet = await ref.read(myOutletProvider.future);
    await ApiClient.dio.post('/api/slots', data: {
      ...data,
      'outletId': outlet.id,
    });
    ref.invalidate(managerSlotsProvider);
  }
}

final managerProvider = NotifierProvider<ManagerNotifier, void>(() {
  return ManagerNotifier();
});