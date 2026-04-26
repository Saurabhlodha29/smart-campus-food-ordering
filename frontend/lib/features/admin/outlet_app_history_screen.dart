// lib/features/admin/outlet_app_history_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'admin_provider.dart';

class OutletAppHistoryScreen extends ConsumerWidget {
  const OutletAppHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appsAsync = ref.watch(allOutletAppsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Application History'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/admin/dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(allOutletAppsProvider),
          ),
        ],
      ),
      body: appsAsync.when(
        data: (apps) => apps.isEmpty
            ? const Center(child: Text('No applications yet.'))
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: apps.length,
                itemBuilder: (context, index) {
                  final app = apps[index];
                  final statusColor = switch (app.status) {
                    'APPROVED' => Colors.green,
                    'REJECTED' => Colors.red,
                    _ => Colors.orange,
                  };
                  return Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(app.outletName,
                                    style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 15)),
                                const SizedBox(height: 4),
                                Text(app.managerName,
                                    style: const TextStyle(
                                        color: Colors.grey, fontSize: 13)),
                                Text(app.managerEmail,
                                    style: const TextStyle(
                                        color: Colors.grey, fontSize: 13)),
                                if (app.rejectionReason != null) ...[
                                  const SizedBox(height: 4),
                                  Text('Reason: ${app.rejectionReason}',
                                      style: const TextStyle(
                                          color: Colors.red,
                                          fontSize: 12)),
                                ],
                              ],
                            ),
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: statusColor.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  app.status,
                                  style: TextStyle(
                                      color: statusColor,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text('Attempt ${app.attemptNumber}/3',
                                  style: const TextStyle(
                                      color: Colors.grey, fontSize: 11)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}