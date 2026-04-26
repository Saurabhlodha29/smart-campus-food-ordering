// lib/features/student/student_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/api/api_client.dart';
import '../../core/models/outlet_model.dart';
import '../../core/models/menu_item_model.dart';
import '../../core/models/pickup_slot_model.dart';
import '../../core/models/order_model.dart';

// ---------------------------------------------------------------------------
// OUTLETS
// ---------------------------------------------------------------------------

final studentOutletsProvider = FutureProvider<List<Outlet>>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  final campusId = prefs.getString('campusId') ?? '';
  if (campusId.isEmpty) throw Exception('Campus ID not found. Please log in again.');
  final response = await ApiClient.dio.get('/api/outlets/campus/$campusId');
  return (response.data as List).map((o) => Outlet.fromJson(o)).toList();
});

// ---------------------------------------------------------------------------
// MENU ITEMS
// ---------------------------------------------------------------------------

final menuItemsProvider =
    FutureProvider.family<List<MenuItem>, int>((ref, outletId) async {
  final response = await ApiClient.dio.get('/api/menu-items?outletId=$outletId');
  return (response.data as List).map((m) => MenuItem.fromJson(m)).toList();
});

// ---------------------------------------------------------------------------
// PICKUP SLOTS — returns all, filter client-side
// ---------------------------------------------------------------------------

final pickupSlotsProvider =
    FutureProvider.family<List<PickupSlot>, int>((ref, outletId) async {
  final response = await ApiClient.dio.get('/api/slots');
  final all = (response.data as List).map((s) => PickupSlot.fromJson(s)).toList();
  // Filter by outletId if backend returns it, otherwise show all slots
  // If outletId comes back as 0 it means backend does not include it in response
  final filtered = all.where((s) => s.outletId == outletId).toList();
  return filtered.isNotEmpty ? filtered : all;
});

// ---------------------------------------------------------------------------
// ORDERS
// ---------------------------------------------------------------------------

final myOrdersProvider = FutureProvider<List<Order>>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  final studentId = prefs.getString('userId') ?? '';
  if (studentId.isEmpty) throw Exception('User ID not found.');
  final response = await ApiClient.dio.get('/api/orders/student/$studentId');
  return (response.data as List).map((o) => Order.fromJson(o)).toList();
});

// ---------------------------------------------------------------------------
// CART STATE
// ---------------------------------------------------------------------------

class CartItem {
  final MenuItem item;
  int quantity;
  CartItem({required this.item, this.quantity = 1});
}

class CartNotifier extends Notifier<List<CartItem>> {
  @override
  List<CartItem> build() => [];

  void addItem(MenuItem item) {
    final existing = state.where((c) => c.item.id == item.id).toList();
    if (existing.isEmpty) {
      state = [...state, CartItem(item: item)];
    } else {
      state = [
        for (final c in state)
          if (c.item.id == item.id)
            CartItem(item: c.item, quantity: c.quantity + 1)
          else
            c
      ];
    }
  }

  void removeItem(int itemId) {
    state = state.where((c) => c.item.id != itemId).toList();
  }

  void decreaseItem(int itemId) {
    final existing = state.where((c) => c.item.id == itemId).toList();
    if (existing.isEmpty) return;
    if (existing.first.quantity <= 1) {
      removeItem(itemId);
    } else {
      state = [
        for (final c in state)
          if (c.item.id == itemId)
            CartItem(item: c.item, quantity: c.quantity - 1)
          else
            c
      ];
    }
  }

  void clear() => state = [];

  double get total =>
      state.fold(0, (sum, c) => sum + c.item.price * c.quantity);

  int get itemCount => state.fold(0, (sum, c) => sum + c.quantity);
}

final cartProvider = NotifierProvider<CartNotifier, List<CartItem>>(() {
  return CartNotifier();
});

// ---------------------------------------------------------------------------
// SELECTED SLOT
// ---------------------------------------------------------------------------

class SelectedSlotNotifier extends Notifier<PickupSlot?> {
  @override
  PickupSlot? build() => null;
  void set(PickupSlot? slot) => state = slot;
}

final selectedSlotProvider =
    NotifierProvider<SelectedSlotNotifier, PickupSlot?>(
        () => SelectedSlotNotifier());

// ---------------------------------------------------------------------------
// PAYMENT MODE
// ---------------------------------------------------------------------------

class PaymentModeNotifier extends Notifier<String> {
  @override
  String build() => 'ONLINE';
  void set(String mode) => state = mode;
}

final paymentModeProvider =
    NotifierProvider<PaymentModeNotifier, String>(() => PaymentModeNotifier());

// ---------------------------------------------------------------------------
// CURRENT OUTLET ID — set when student enters outlet detail screen
// ---------------------------------------------------------------------------

class CurrentOutletIdNotifier extends Notifier<int> {
  @override
  int build() => 0;
  void set(int id) => state = id;
}

final currentOutletIdProvider =
    NotifierProvider<CurrentOutletIdNotifier, int>(() => CurrentOutletIdNotifier());

// ---------------------------------------------------------------------------
// PLACE ORDER
// ---------------------------------------------------------------------------

class OrderNotifier extends Notifier<AsyncValue<Order?>> {
  @override
  AsyncValue<Order?> build() => const AsyncValue.data(null);

  Future<Order?> placeOrder({
    required List<CartItem> cartItems,
    required int slotId,
    required String paymentMode,
    required int outletId,
  }) async {
    state = const AsyncValue.loading();
    try {
      final prefs = await SharedPreferences.getInstance();
      final studentId = int.parse(prefs.getString('userId') ?? '0');

      final items = cartItems
          .map((c) => {'menuItemId': c.item.id, 'quantity': c.quantity})
          .toList();

      final response = await ApiClient.dio.post('/api/orders', data: {
        'studentId': studentId,
        'slotId': slotId,
        'outletId': outletId,
        'paymentMode': paymentMode,
        'items': items,
      });

      final order = Order.fromJson(response.data);
      state = AsyncValue.data(order);
      return order;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return null;
    }
  } // ← closes placeOrder
} // ← closes OrderNotifier

final orderNotifierProvider =
    NotifierProvider<OrderNotifier, AsyncValue<Order?>>(() {
  return OrderNotifier();
});