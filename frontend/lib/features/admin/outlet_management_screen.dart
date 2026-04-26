// lib/features/admin/outlet_management_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'admin_provider.dart';

class OutletManagementScreen extends ConsumerWidget {
  const OutletManagementScreen({super.key});

  Color _statusColor(String status) => switch (status) {
        'ACTIVE' => Colors.green,
        'SUSPENDED' => Colors.red,
        'PENDING_LAUNCH' => Colors.amber,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outletsAsync = ref.watch(campusOutletsAdminProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Manage Outlets'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/admin/dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(campusOutletsAdminProvider),
          ),
        ],
      ),
      body: outletsAsync.when(
        data: (outlets) => outlets.isEmpty
            ? const Center(child: Text('No outlets on this campus yet.'))
            : RefreshIndicator(
                onRefresh: () async =>
                    ref.invalidate(campusOutletsAdminProvider),
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: outlets.length,
                  itemBuilder: (context, index) {
                    final outlet = outlets[index];
                    final color = _statusColor(outlet.status);
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.storefront,
                                    color: Colors.deepOrange),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(outlet.name,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 15)),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: color.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(outlet.status,
                                      style: TextStyle(
                                          color: color,
                                          fontWeight: FontWeight.w600,
                                          fontSize: 12)),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text('~${outlet.avgPrepTime} min avg prep time',
                                style: const TextStyle(
                                    color: Colors.grey, fontSize: 13)),
                            if (outlet.launchedAt != null)
                              Text(
                                  'Launched: ${outlet.launchedAt!.substring(0, 10)}',
                                  style: const TextStyle(
                                      color: Colors.grey, fontSize: 13)),
                            const SizedBox(height: 12),

                            // Action buttons based on status
                            if (outlet.status == 'ACTIVE')
                              SizedBox(
                                width: double.infinity,
                                child: OutlinedButton.icon(
                                  icon: const Icon(Icons.pause_circle_outline,
                                      color: Colors.red),
                                  label: const Text('Suspend Outlet',
                                      style: TextStyle(color: Colors.red)),
                                  style: OutlinedButton.styleFrom(
                                    side: const BorderSide(color: Colors.red),
                                  ),
                                  onPressed: () async {
                                    final confirm = await _confirmDialog(
                                        context,
                                        'Suspend "${outlet.name}"?',
                                        'Students will not be able to order from this outlet.',
                                        Colors.red);
                                    if (confirm == true) {
                                      await ref
                                          .read(adminProvider.notifier)
                                          .suspendOutlet(outlet.id);
                                    }
                                  },
                                ),
                              ),

                            if (outlet.status == 'SUSPENDED')
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton.icon(
                                  icon: const Icon(Icons.play_circle_outline),
                                  label: const Text('Reactivate Outlet'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.green,
                                    foregroundColor: Colors.white,
                                  ),
                                  onPressed: () async {
                                    final confirm = await _confirmDialog(
                                        context,
                                        'Reactivate "${outlet.name}"?',
                                        'Students will be able to order again.',
                                        Colors.green);
                                    if (confirm == true) {
                                      await ref
                                          .read(adminProvider.notifier)
                                          .reactivateOutlet(outlet.id);
                                    }
                                  },
                                ),
                              ),

                            if (outlet.status == 'PENDING_LAUNCH')
                              const Text(
                                'Waiting for manager to add items and launch.',
                                style: TextStyle(
                                    color: Colors.amber, fontSize: 13),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }

  Future<bool?> _confirmDialog(BuildContext context, String title,
      String message, Color color) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text('Confirm',
                  style: TextStyle(color: color))),
        ],
      ),
    );
  }
}