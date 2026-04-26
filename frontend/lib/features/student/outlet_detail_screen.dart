// lib/features/student/outlet_detail_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/menu_item_model.dart';
import '../../core/models/pickup_slot_model.dart';
import '../../core/theme/app_theme.dart';
import 'student_provider.dart';

class OutletDetailScreen extends ConsumerStatefulWidget {
  final String outletId;
  const OutletDetailScreen({super.key, required this.outletId});

  @override
  ConsumerState<OutletDetailScreen> createState() => _OutletDetailScreenState();
}

class _OutletDetailScreenState extends ConsumerState<OutletDetailScreen> {
  @override
  void initState() {
    super.initState();
    // Set the current outlet ID so cart_screen can use the real outletId
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(currentOutletIdProvider.notifier).set(int.parse(widget.outletId));
    });
  }

  @override
  Widget build(BuildContext context) {
    final id = int.parse(widget.outletId);
    final menuAsync = ref.watch(menuItemsProvider(id));
    final slotsAsync = ref.watch(pickupSlotsProvider(id));
    final cart = ref.watch(cartProvider);
    final selectedSlot = ref.watch(selectedSlotProvider);
    final cartNotifier = ref.read(cartProvider.notifier);

    int qtyInCart(int itemId) {
      final match = cart.where((c) => c.item.id == itemId);
      return match.isEmpty ? 0 : match.first.quantity;
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: menuAsync.when(
        data: (items) => CustomScrollView(
          slivers: [
            // --- HEADER (SliverAppBar) ---
            SliverAppBar(
              expandedHeight: 200.0,
              pinned: true,
              backgroundColor: AppTheme.background,
              leading: Container(
                margin: const EdgeInsets.all(8),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.black),
                  onPressed: () => context.pop(),
                ),
              ),
              actions: [
                if (cart.isNotEmpty)
                  Container(
                    margin: const EdgeInsets.all(8),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      onPressed: () => context.push('/student/cart'),
                      icon: const Icon(Icons.shopping_cart, color: AppTheme.primary),
                    ),
                  ),
              ],
              flexibleSpace: FlexibleSpaceBar(
                title: const Text('Menu', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, shadows: [Shadow(color: Colors.black, blurRadius: 4)])),
                background: Image.network(
                  'https://images.unsplash.com/photo-1552566626-52f8b828add9?w=600&q=80',
                  fit: BoxFit.cover,
                  color: Colors.black26,
                  colorBlendMode: BlendMode.darken,
                ),
              ),
            ),

            // --- PICKUP SLOT SECTION ---
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Select Pickup Slot',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    slotsAsync.when(
                      data: (slots) => slots.isEmpty
                          ? const Text('No slots available today.',
                              style: TextStyle(color: Colors.grey))
                          : SizedBox(
                              height: 100,
                              child: ListView.builder(
                                scrollDirection: Axis.horizontal,
                                itemCount: slots.length,
                                itemBuilder: (context, index) {
                                  final slot = slots[index];
                                  final isSelected =
                                      selectedSlot?.id == slot.id;
                                  return _SlotCard(
                                    slot: slot,
                                    isSelected: isSelected,
                                    onTap: slot.isFull
                                        ? null
                                        : () => ref
                                            .read(selectedSlotProvider.notifier)
                                            .set(slot),
                                  );
                                },
                              ),
                            ),
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (e, _) =>
                          Text('Could not load slots: $e'),
                    ),
                    const Divider(height: 24),
                    const Text('Menu',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                  ],
                ),
              ),
            ),

            // --- MENU ITEMS ---
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final item = items[index];
                    final qty = qtyInCart(item.id);
                    return _MenuItemRow(
                      item: item,
                      qty: qty,
                      onAdd: item.isAvailable
                          ? () => cartNotifier.addItem(item)
                          : null,
                      onIncrease: () => cartNotifier.addItem(item),
                      onDecrease: () => cartNotifier.decreaseItem(item.id),
                    );
                  },
                  childCount: items.length,
                ),
              ),
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),

      // Bottom bar — go to cart
      bottomNavigationBar: cart.isEmpty
          ? null
          : SafeArea(
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                decoration: BoxDecoration(
                  color: AppTheme.background,
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -5))
                  ],
                ),
                child: ElevatedButton(
                  onPressed: selectedSlot == null
                      ? null // disabled until slot selected
                      : () => context.push('/student/cart'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    disabledBackgroundColor: Colors.grey[300],
                  ),
                  child: Text(
                    selectedSlot == null
                        ? 'Select a time slot to continue'
                        : 'View Cart (${cartNotifier.itemCount} items) • ₹${cartNotifier.total.toStringAsFixed(2)}',
                  ),
                ),
              ),
            ),
    );
  }
}

// --- SLOT CARD WIDGET ---
class _SlotCard extends StatelessWidget {
  final PickupSlot slot;
  final bool isSelected;
  final VoidCallback? onTap;

  const _SlotCard({required this.slot, required this.isSelected, this.onTap});

  @override
  Widget build(BuildContext context) {
    final isFull = slot.isFull;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 110,
        margin: const EdgeInsets.only(right: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isFull
              ? Colors.grey[100]
              : isSelected
                  ? AppTheme.primary.withOpacity(0.1)
                  : Colors.white,
          border: Border.all(
            color: isFull
                ? Colors.grey.shade300
                : isSelected
                    ? AppTheme.primary
                    : Colors.grey.shade300,
            width: isSelected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              slot.startTime,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: isSelected && !isFull ? AppTheme.primary : AppTheme.text,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              isFull ? 'Full' : '${slot.maxOrders - slot.currentOrders} left',
              style: TextStyle(
                fontSize: 11,
                color: isFull ? Colors.red : (isSelected ? AppTheme.primary : Colors.grey),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// --- MENU ITEM ROW WIDGET ---
class _MenuItemRow extends StatelessWidget {
  final MenuItem item;
  final int qty;
  final VoidCallback? onAdd;
  final VoidCallback onIncrease;
  final VoidCallback onDecrease;

  const _MenuItemRow({
    required this.item,
    required this.qty,
    this.onAdd,
    required this.onIncrease,
    required this.onDecrease,
  });

  @override
  Widget build(BuildContext context) {
    final isUnavailable = !item.isAvailable;

    return Opacity(
      opacity: isUnavailable ? 0.5 : 1.0,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20.0),
          boxShadow: AppTheme.softShadows,
        ),
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Photo
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Stack(
                children: [
                  Container(
                    width: 90,
                    height: 90,
                    color: AppTheme.surface,
                    child: item.photoUrl != null
                        ? Image.network(item.photoUrl!,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const Icon(
                                Icons.fastfood,
                                color: Colors.grey))
                        : const Icon(Icons.fastfood, color: Colors.grey),
                  ),
                  // Out of stock overlay
                  if (isUnavailable)
                    Positioned.fill(
                      child: Container(
                        color: Colors.black45,
                        child: const Center(
                          child: Text('Out of\nStock',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 16),

            // Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.text)),
                  const SizedBox(height: 4),
                  Text('~${item.prepTime} min',
                      style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('₹${item.price.toStringAsFixed(2)}',
                          style: const TextStyle(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.bold,
                              fontSize: 16)),
                      if (!isUnavailable)
                        qty == 0
                            ? SizedBox(
                                height: 32,
                                child: ElevatedButton(
                                  onPressed: onAdd,
                                  style: ElevatedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(horizontal: 16),
                                    backgroundColor: AppTheme.primary.withOpacity(0.1),
                                    foregroundColor: AppTheme.primary,
                                    elevation: 0,
                                  ),
                                  child: const Text('ADD'),
                                ),
                              )
                            : Row(
                                children: [
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    onPressed: onDecrease,
                                    icon: const Icon(Icons.remove_circle, color: AppTheme.primary, size: 28),
                                  ),
                                  const SizedBox(width: 12),
                                  Text('$qty', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                  const SizedBox(width: 12),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    onPressed: onIncrease,
                                    icon: const Icon(Icons.add_circle, color: AppTheme.primary, size: 28),
                                  ),
                                ],
                              ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}