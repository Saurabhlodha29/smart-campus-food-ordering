// lib/features/student/cart_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import 'student_provider.dart';

class CartScreen extends ConsumerWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartProvider);
    final cartNotifier = ref.read(cartProvider.notifier);
    final selectedSlot = ref.watch(selectedSlotProvider);
    final paymentMode = ref.watch(paymentModeProvider);
    final orderState = ref.watch(orderNotifierProvider);
    final currentOutletId = ref.watch(currentOutletIdProvider);

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Your Cart'),
        actions: [
          if (cart.isNotEmpty)
            TextButton(
              onPressed: () => cartNotifier.clear(),
              child: const Text('Clear', style: TextStyle(color: Colors.red)),
            ),
        ],
      ),
      body: cart.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.shopping_cart_outlined, size: 80, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('Your cart is empty',
                      style: TextStyle(fontSize: 18, color: Colors.grey)),
                ],
              ),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Cart items
                ...cart.map((cartItem) => Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: AppTheme.softShadows,
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(cartItem.item.name,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold, fontSize: 16)),
                                  const SizedBox(height: 4),
                                  Text(
                                      '₹${cartItem.item.price.toStringAsFixed(2)}',
                                      style: const TextStyle(color: Colors.grey)),
                                ],
                              ),
                            ),
                            Row(
                              children: [
                                IconButton(
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  icon: const Icon(Icons.remove_circle,
                                      color: AppTheme.primary, size: 28),
                                  onPressed: () =>
                                      cartNotifier.decreaseItem(cartItem.item.id),
                                ),
                                const SizedBox(width: 12),
                                Text('${cartItem.quantity}',
                                    style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16)),
                                const SizedBox(width: 12),
                                IconButton(
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  icon: const Icon(Icons.add_circle,
                                      color: AppTheme.primary, size: 28),
                                  onPressed: () =>
                                      cartNotifier.addItem(cartItem.item),
                                ),
                              ],
                            ),
                            SizedBox(
                              width: 70,
                              child: Text(
                                '₹${(cartItem.item.price * cartItem.quantity).toStringAsFixed(2)}',
                                textAlign: TextAlign.right,
                                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )),

                const SizedBox(height: 8),
                const Divider(),

                // Selected slot info
                if (selectedSlot != null)
                  ListTile(
                    leading: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.1), shape: BoxShape.circle),
                      child: const Icon(Icons.access_time, color: AppTheme.primary),
                    ),
                    title: const Text('Pickup Slot', style: TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text('${selectedSlot.startTime} – ${selectedSlot.endTime}'),
                    contentPadding: EdgeInsets.zero,
                  ),

                const Divider(),

                // Payment mode selector
                const Text('Payment Mode',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _PaymentOption(
                        label: 'Online',
                        icon: Icons.phone_android,
                        selected: paymentMode == 'ONLINE',
                        // FIX: use .set() instead of .state = 
                        onTap: () => ref.read(paymentModeProvider.notifier).set('ONLINE'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _PaymentOption(
                        label: 'Cash on Delivery',
                        icon: Icons.money,
                        selected: paymentMode == 'COD',
                        onTap: () => ref.read(paymentModeProvider.notifier).set('COD'),
                      ),
                    ),
                  ],
                ),

                const Divider(height: 32),

                // Total
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Total',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text(
                      '₹${cartNotifier.total.toStringAsFixed(2)}',
                      style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primary),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Error message
                if (orderState is AsyncError)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      'Order failed: ${(orderState as AsyncError).error}',
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                  ),

ElevatedButton(
  onPressed: (orderState is AsyncLoading || selectedSlot == null)
      ? null
      : () async {
          final order = await ref
              .read(orderNotifierProvider.notifier)
              .placeOrder(
                cartItems: cart,
                slotId: selectedSlot.id,
                paymentMode: paymentMode,
                outletId: currentOutletId,
              );
          if (order != null && context.mounted) {
            cartNotifier.clear();
            context.go('/student/order-confirm', extra: order);
          }
        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: orderState is AsyncLoading
                      ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(
                          selectedSlot == null
                              ? 'Go back and select a slot'
                              : 'Place Order',
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                ),
                const SizedBox(height: 24),
              ],
            ),
    );
  }
}

class _PaymentOption extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  const _PaymentOption({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary : AppTheme.surface,
          border: Border.all(
              color: selected ? AppTheme.primary : Colors.grey.shade300),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: selected ? Colors.white : Colors.grey, size: 20),
            const SizedBox(width: 8),
            Text(label,
                style: TextStyle(
                    color: selected ? Colors.white : AppTheme.text,
                    fontWeight: FontWeight.w600,
                    fontSize: 14)),
          ],
        ),
      ),
    );
  }
}