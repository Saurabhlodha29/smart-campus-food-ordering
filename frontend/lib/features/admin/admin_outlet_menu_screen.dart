// lib/features/admin/admin_outlet_menu_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/menu_item_model.dart';
import 'admin_provider.dart';

class AdminOutletMenuScreen extends ConsumerWidget {
  final int outletId;
  final String outletName;

  const AdminOutletMenuScreen({
    super.key,
    required this.outletId,
    required this.outletName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final menuAsync = ref.watch(adminOutletMenuProvider(outletId));

    return Scaffold(
      appBar: AppBar(
        title: Text('$outletName — Menu'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(adminOutletMenuProvider(outletId)),
          ),
        ],
      ),
      body: menuAsync.when(
        data: (items) {
          if (items.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.no_food, size: 64, color: const Color(0xFF64748B)),
                  SizedBox(height: 12),
                  Text('No menu items yet.',
                      style: TextStyle(color: const Color(0xFF64748B), fontSize: 16)),
                ],
              ),
            );
          }

          final available = items.where((i) => i.isAvailable).toList();
          final unavailable = items.where((i) => !i.isAvailable).toList();

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('${items.length} items total',
                  style: const TextStyle(color: const Color(0xFF64748B), fontSize: 13)),
              const SizedBox(height: 12),
              if (available.isNotEmpty) ...[
                _sectionHeader('Available', const Color(0xFF10B981)),
                const SizedBox(height: 8),
                ...available.map((item) => _MenuItemCard(item: item)),
                const SizedBox(height: 16),
              ],
              if (unavailable.isNotEmpty) ...[
                _sectionHeader('Out of Stock', const Color(0xFF64748B)),
                const SizedBox(height: 8),
                ...unavailable.map((item) => _MenuItemCard(item: item)),
              ],
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: const Color(0xFFEF4444)),
              const SizedBox(height: 12),
              Text('$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () =>
                    ref.invalidate(adminOutletMenuProvider(outletId)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionHeader(String label, Color color) {
    return Row(
      children: [
        Container(
          width: 4,
          height: 18,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(label,
            style: TextStyle(
                fontWeight: FontWeight.bold, fontSize: 15, color: color)),
      ],
    );
  }
}

class _MenuItemCard extends StatelessWidget {
  final MenuItem item;
  const _MenuItemCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: item.isAvailable ? 1.0 : 0.55,
      child: Card(
        margin: const EdgeInsets.only(bottom: 10),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: item.photoUrl != null
                    ? Image.network(
                        item.photoUrl!,
                        width: 64,
                        height: 64,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => _placeholder(),
                      )
                    : _placeholder(),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.name,
                        style: const TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          '₹${item.price.toStringAsFixed(2)}',
                          style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              color: const Color(0xFFFF5722),
                              fontSize: 15),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '· ${item.prepTime} min',
                          style: const TextStyle(
                              color: const Color(0xFF64748B), fontSize: 12),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: item.isAvailable
                            ? const Color(0xFF10B981).withOpacity(0.2)
                            : Colors.grey[100],
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                            color: item.isAvailable
                                ? const Color(0xFF10B981)
                                : const Color(0xFF64748B)),
                      ),
                      child: Text(
                        item.isAvailable ? 'Available' : 'Out of Stock',
                        style: TextStyle(
                            fontSize: 10,
                            color:
                                item.isAvailable ? const Color(0xFF10B981) : const Color(0xFF64748B),
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _placeholder() => Container(
        width: 64,
        height: 64,
        color: Colors.grey[200],
        child: const Icon(Icons.fastfood, color: const Color(0xFF64748B), size: 30),
      );
}