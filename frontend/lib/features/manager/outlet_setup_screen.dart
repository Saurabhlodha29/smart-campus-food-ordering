// lib/features/manager/outlet_setup_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'manager_provider.dart';

class OutletSetupScreen extends ConsumerStatefulWidget {
  const OutletSetupScreen({super.key});

  @override
  ConsumerState<OutletSetupScreen> createState() => _OutletSetupScreenState();
}

class _OutletSetupScreenState extends ConsumerState<OutletSetupScreen> {
  bool _launching = false;

  Future<void> _launchOutlet() async {
    setState(() => _launching = true);
    try {
      final outlet = await ref.read(myOutletProvider.future);
      await ref.read(managerProvider.notifier).launchOutlet(outlet.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('🚀 Outlet launched successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        context.go('/manager/dashboard');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Launch failed: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _launching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final menuAsync = ref.watch(managerMenuProvider);
    final outletAsync = ref.watch(myOutletProvider);

    final itemCount = menuAsync.when(
      data: (items) => items.length,
      loading: () => 0,
      error: (_, __) => 0,
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Setup Your Outlet'),
        automaticallyImplyLeading: false,
      ),
      body: Column(
        children: [
          // Status banner
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: Colors.amber[50],
            child: Column(
              children: [
                const Icon(Icons.storefront, size: 48, color: Colors.amber),
                const SizedBox(height: 8),
                outletAsync.when(
                  data: (o) => Text(o.name,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.bold)),
                  loading: () => const CircularProgressIndicator(),
                  error: (_, __) => const Text('Your Outlet'),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Add at least 1 menu item before launching.',
                  style: TextStyle(color: Colors.grey),
                ),
              ],
            ),
          ),

          // Menu items list
          Expanded(
            child: menuAsync.when(
              data: (items) => items.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.restaurant_menu,
                              size: 64, color: Colors.grey),
                          SizedBox(height: 12),
                          Text('No menu items yet.',
                              style: TextStyle(color: Colors.grey)),
                          SizedBox(height: 4),
                          Text('Add your first item below.',
                              style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: items.length,
                      itemBuilder: (context, index) {
                        final item = items[index];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            leading: const Icon(Icons.fastfood,
                                color: Colors.deepOrange),
                            title: Text(item.name),
                            subtitle: Text(
                                '₹${item.price.toStringAsFixed(2)} · ~${item.prepTime} min'),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete_outline,
                                  color: Colors.red),
                              onPressed: () async {
                                await ref
                                    .read(managerProvider.notifier)
                                    .deleteMenuItem(item.id);
                              },
                            ),
                          ),
                        );
                      },
                    ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Error: $e')),
            ),
          ),

          // Bottom buttons
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Add item button
                  OutlinedButton.icon(
                    onPressed: () => _showAddItemDialog(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Add Menu Item'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 48),
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Launch button — disabled until at least 1 item
                  ElevatedButton.icon(
                    onPressed: itemCount == 0 || _launching ? null : _launchOutlet,
                    icon: _launching
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2))
                        : const Icon(Icons.rocket_launch),
                    label: Text(itemCount == 0
                        ? 'Add items to launch'
                        : 'Launch Outlet ($itemCount items)'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 52),
                      disabledBackgroundColor: Colors.grey[300],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showAddItemDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final priceCtrl = TextEditingController();
    final prepCtrl = TextEditingController();
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
              const Text('Add Menu Item',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
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
                      validator: (v) =>
                          v!.isEmpty ? 'Required' : null,
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
                      validator: (v) =>
                          v!.isEmpty ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () async {
                  if (!formKey.currentState!.validate()) return;
                  await ref.read(managerProvider.notifier).addMenuItem({
                    'name': nameCtrl.text.trim(),
                    'price': double.parse(priceCtrl.text),
                    'prepTime': int.parse(prepCtrl.text),
                    'photoUrl': 'https://via.placeholder.com/150',
                  });
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepOrange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: const Text('Add Item'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}