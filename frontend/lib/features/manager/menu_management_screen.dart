// lib/features/manager/menu_management_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/menu_item_model.dart';
import 'manager_provider.dart';

class MenuManagementScreen extends ConsumerWidget {
  const MenuManagementScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final menuAsync = ref.watch(managerMenuProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Menu Management'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/manager/dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(managerMenuProvider),
          ),
        ],
      ),
      body: menuAsync.when(
        data: (items) => items.isEmpty
            ? const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.restaurant_menu, size: 64, color: Colors.grey),
                    SizedBox(height: 12),
                    Text('No menu items yet.',
                        style: TextStyle(color: Colors.grey)),
                  ],
                ),
              )
            : RefreshIndicator(
                onRefresh: () async => ref.invalidate(managerMenuProvider),
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return _MenuItemCard(item: item);
                  },
                ),
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddEditDialog(context, ref, null),
        backgroundColor: Colors.deepOrange,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('Add Item', style: TextStyle(color: Colors.white)),
      ),
    );
  }

  void _showAddEditDialog(BuildContext context, WidgetRef ref, MenuItem? existing) {
    final nameCtrl = TextEditingController(text: existing?.name);
    final priceCtrl =
        TextEditingController(text: existing?.price.toString() ?? '');
    final prepCtrl =
        TextEditingController(text: existing?.prepTime.toString() ?? '');
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24, right: 24, top: 24,
        ),
        child: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(existing == null ? 'Add Menu Item' : 'Edit ${existing.name}',
                  style: const TextStyle(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              TextFormField(
                controller: nameCtrl,
                decoration: const InputDecoration(
                    labelText: 'Item Name', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: priceCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Price (₹)', border: OutlineInputBorder()),
                      keyboardType: TextInputType.number,
                      validator: (v) => v!.isEmpty ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: prepCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Prep Time (min)',
                          border: OutlineInputBorder()),
                      keyboardType: TextInputType.number,
                      validator: (v) => v!.isEmpty ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () async {
                  if (!formKey.currentState!.validate()) return;
                  final data = {
                    'name': nameCtrl.text.trim(),
                    'price': double.parse(priceCtrl.text),
                    'prepTime': int.parse(prepCtrl.text),
                    'photoUrl': existing?.photoUrl ?? 'https://via.placeholder.com/150',
                  };
                  if (existing == null) {
                    await ref.read(managerProvider.notifier).addMenuItem(data);
                  } else {
                    await ref
                        .read(managerProvider.notifier)
                        .editMenuItem(existing.id, data);
                  }
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepOrange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: Text(existing == null ? 'Add Item' : 'Save Changes'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _MenuItemCard extends ConsumerWidget {
  final MenuItem item;
  const _MenuItemCard({required this.item});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // Photo
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Container(
                width: 60,
                height: 60,
                color: Colors.grey[200],
                child: item.photoUrl != null
                    ? Image.network(item.photoUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            const Icon(Icons.fastfood, color: Colors.grey))
                    : const Icon(Icons.fastfood, color: Colors.grey),
              ),
            ),
            const SizedBox(width: 12),
            // Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.name,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text('₹${item.price.toStringAsFixed(2)} · ~${item.prepTime} min',
                      style: const TextStyle(color: Colors.grey, fontSize: 13)),
                ],
              ),
            ),
            // Availability toggle
            Column(
              children: [
                Switch(
                  value: item.isAvailable,
                  activeColor: Colors.green,
                  onChanged: (val) async {
                    await ref
                        .read(managerProvider.notifier)
                        .toggleAvailability(item.id, val);
                  },
                ),
                Text(
                  item.isAvailable ? 'Available' : 'Sold Out',
                  style: TextStyle(
                    fontSize: 10,
                    color: item.isAvailable ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ),
            // Edit + Delete
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'edit') {
                  _MenuManagementScreen_showEdit(context, ref, item);
                } else if (value == 'delete') {
                  final confirm = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('Delete Item?'),
                      content: Text('Remove "${item.name}" from menu?'),
                      actions: [
                        TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: const Text('Cancel')),
                        TextButton(
                            onPressed: () => Navigator.pop(ctx, true),
                            child: const Text('Delete',
                                style: TextStyle(color: Colors.red))),
                      ],
                    ),
                  );
                  if (confirm == true) {
                    await ref
                        .read(managerProvider.notifier)
                        .deleteMenuItem(item.id);
                  }
                }
              },
              itemBuilder: (_) => [
                const PopupMenuItem(value: 'edit', child: Text('Edit')),
                const PopupMenuItem(
                    value: 'delete',
                    child: Text('Delete', style: TextStyle(color: Colors.red))),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _MenuManagementScreen_showEdit(
      BuildContext context, WidgetRef ref, MenuItem item) {
    final nameCtrl = TextEditingController(text: item.name);
    final priceCtrl = TextEditingController(text: item.price.toString());
    final prepCtrl = TextEditingController(text: item.prepTime.toString());
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24, right: 24, top: 24,
        ),
        child: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Edit ${item.name}',
                  style: const TextStyle(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              TextFormField(
                controller: nameCtrl,
                decoration: const InputDecoration(
                    labelText: 'Item Name', border: OutlineInputBorder()),
                validator: (v) => v!.isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: priceCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Price (₹)', border: OutlineInputBorder()),
                      keyboardType: TextInputType.number,
                      validator: (v) => v!.isEmpty ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: prepCtrl,
                      decoration: const InputDecoration(
                          labelText: 'Prep Time (min)',
                          border: OutlineInputBorder()),
                      keyboardType: TextInputType.number,
                      validator: (v) => v!.isEmpty ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () async {
                  if (!formKey.currentState!.validate()) return;
                  await ref.read(managerProvider.notifier).editMenuItem(item.id, {
                    'name': nameCtrl.text.trim(),
                    'price': double.parse(priceCtrl.text),
                    'prepTime': int.parse(prepCtrl.text),
                    'photoUrl': item.photoUrl ?? 'https://via.placeholder.com/150',
                  });
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepOrange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: const Text('Save Changes'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}