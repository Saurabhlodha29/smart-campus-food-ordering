// lib/features/manager/manager_dashboard_screen.dart

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/order_model.dart';
import '../../core/storage/secure_storage.dart';
import 'manager_provider.dart';

class ManagerDashboardScreen extends ConsumerStatefulWidget {
  const ManagerDashboardScreen({super.key});

  @override
  ConsumerState<ManagerDashboardScreen> createState() =>
      _ManagerDashboardScreenState();
}

class _ManagerDashboardScreenState
    extends ConsumerState<ManagerDashboardScreen> {
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    // Check outlet status — redirect to setup if not yet launched
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      try {
        final outlet = await ref.read(myOutletProvider.future);
        if (outlet.status == 'PENDING_LAUNCH' && mounted) {
          context.go('/manager/setup');
          return;
        }
      } catch (_) {}
      // Only start polling if we stay on dashboard
      _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) {
        if (mounted) ref.invalidate(managerOrdersProvider);
      });
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _logout(BuildContext context) async {
    await StorageService.clearAll();
    if (context.mounted) context.go('/login');
  }

  Color _statusColor(String status) => switch (status) {
        'PLACED' => Colors.blue,
        'PREPARING' => Colors.orange,
        'READY' => Colors.green,
        'PICKED' => Colors.grey,
        'EXPIRED' => Colors.red,
        _ => Colors.grey,
      };

  String _nextStatus(String current) => switch (current) {
        'PLACED' => 'PREPARING',
        'PREPARING' => 'READY',
        'READY' => 'PICKED',
        _ => '',
      };

  String _nextLabel(String current) => switch (current) {
        'PLACED' => 'Mark Preparing',
        'PREPARING' => 'Mark Ready',
        'READY' => 'Mark Picked',
        _ => '',
      };

  @override
  Widget build(BuildContext context) {
    final ordersAsync = ref.watch(managerOrdersProvider);
    final outletAsync = ref.watch(myOutletProvider);

    return Scaffold(
      appBar: AppBar(
        title: outletAsync.when(
          data: (o) => Text(o.name),
          loading: () => const Text('Dashboard'),
          error: (_, __) => const Text('Dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.restaurant_menu),
            tooltip: 'Menu',
            onPressed: () => context.go('/manager/menu'),
          ),
          IconButton(
            icon: const Icon(Icons.schedule),
            tooltip: 'Slots',
            onPressed: () => context.go('/manager/slots'),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(managerOrdersProvider),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => _logout(context),
          ),
        ],
      ),
      body: ordersAsync.when(
        data: (orders) {
          // Show only active orders (not PICKED or EXPIRED)
          final active = orders
              .where((o) => o.status != 'PICKED' && o.status != 'EXPIRED')
              .toList()
            ..sort((a, b) => a.createdAt.compareTo(b.createdAt));

          final done = orders
              .where((o) => o.status == 'PICKED' || o.status == 'EXPIRED')
              .toList()
            ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

          if (orders.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.inbox_outlined, size: 80, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No orders yet!',
                      style: TextStyle(fontSize: 18, color: Colors.grey)),
                  SizedBox(height: 8),
                  Text('Orders will appear here automatically.',
                      style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(managerOrdersProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (active.isNotEmpty) ...[
                  const Text('Active Orders',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  ...active.map((order) => _OrderCard(
                        order: order,
                        statusColor: _statusColor(order.status),
                        nextStatus: _nextStatus(order.status),
                        nextLabel: _nextLabel(order.status),
                        onAction: _nextStatus(order.status).isNotEmpty
                            ? () async {
                                await ref
                                    .read(managerProvider.notifier)
                                    .updateOrderStatus(
                                        order.id, _nextStatus(order.status));
                              }
                            : null,
                      )),
                  const SizedBox(height: 16),
                ],
                if (done.isNotEmpty) ...[
                  const Text('Completed / Expired',
                      style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey)),
                  const SizedBox(height: 8),
                  ...done.take(10).map((order) => _OrderCard(
                        order: order,
                        statusColor: _statusColor(order.status),
                        nextStatus: '',
                        nextLabel: '',
                        onAction: null,
                      )),
                ],
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 12),
              Text('$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => ref.invalidate(managerOrdersProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final Order order;
  final Color statusColor;
  final String nextStatus;
  final String nextLabel;
  final VoidCallback? onAction;

  const _OrderCard({
    required this.order,
    required this.statusColor,
    required this.nextStatus,
    required this.nextLabel,
    this.onAction,
  });

  String _formatTime(DateTime dt) {
    final hour = dt.hour > 12 ? dt.hour - 12 : dt.hour;
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    final min = dt.minute.toString().padLeft(2, '0');
    return '$hour:$min $period';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: statusColor.withOpacity(0.4), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('Order #${order.id}',
                    style: const TextStyle(fontWeight: FontWeight.bold)),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(order.status,
                      style: TextStyle(
                          color: statusColor,
                          fontWeight: FontWeight.w600,
                          fontSize: 12)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('₹${order.totalAmount.toStringAsFixed(2)} · ${order.paymentMode}',
                style: const TextStyle(color: Colors.grey)),
            Text('Ready by ${_formatTime(order.readyAtDate)}',
                style: const TextStyle(color: Colors.grey, fontSize: 13)),
            if (onAction != null) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onAction,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: statusColor,
                    foregroundColor: Colors.white,
                  ),
                  child: Text(nextLabel,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}