// lib/features/manager/manager_ledger_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/order_model.dart';
import 'manager_provider.dart';

// Period selector state
enum LedgerPeriod { daily, weekly, monthly }

final ledgerPeriodProvider =
    NotifierProvider<_LedgerPeriodNotifier, LedgerPeriod>(
        _LedgerPeriodNotifier.new);

class _LedgerPeriodNotifier extends Notifier<LedgerPeriod> {
  @override
  LedgerPeriod build() => LedgerPeriod.daily;
  void set(LedgerPeriod p) => state = p;
}

class ManagerLedgerScreen extends ConsumerWidget {
  const ManagerLedgerScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(managerOrdersProvider);
    final period = ref.watch(ledgerPeriodProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text('Earnings Ledger'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(managerOrdersProvider),
          ),
        ],
      ),
      body: ordersAsync.when(
        data: (orders) {
          // Only count completed (PICKED) orders
          final completed = orders
              .where((o) => o.status == 'PICKED')
              .toList();
          return _LedgerBody(orders: completed, period: period);
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

class _LedgerBody extends ConsumerWidget {
  final List<Order> orders;
  final LedgerPeriod period;

  const _LedgerBody({required this.orders, required this.period});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final grouped = _groupOrders(orders, period);
    final totalEarnings =
        orders.fold<double>(0, (sum, o) => sum + o.totalAmount);

    return Column(
      children: [
        // Period selector
        Padding(
          padding: const EdgeInsets.all(16),
          child: SegmentedButton<LedgerPeriod>(
            segments: const [
              ButtonSegment(
                  value: LedgerPeriod.daily,
                  label: Text('Daily'),
                  icon: Icon(Icons.today)),
              ButtonSegment(
                  value: LedgerPeriod.weekly,
                  label: Text('Weekly'),
                  icon: Icon(Icons.view_week)),
              ButtonSegment(
                  value: LedgerPeriod.monthly,
                  label: Text('Monthly'),
                  icon: Icon(Icons.calendar_month)),
            ],
            selected: {period},
            onSelectionChanged: (sel) =>
                ref.read(ledgerPeriodProvider.notifier).set(sel.first),
          ),
        ),

        // Total summary card
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Card(
            color: const Color(0xFFFF5722),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  const Icon(Icons.account_balance_wallet,
                      color: Colors.white, size: 36),
                  const SizedBox(width: 16),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Total Earnings',
                          style: TextStyle(color: Colors.white70, fontSize: 13)),
                      Text(
                        '₹${totalEarnings.toStringAsFixed(2)}',
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 26,
                            fontWeight: FontWeight.bold),
                      ),
                      Text(
                        '${orders.length} completed orders',
                        style: const TextStyle(
                            color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Grouped list
        if (grouped.isEmpty)
          const Expanded(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.receipt_long_outlined,
                      size: 64, color: const Color(0xFF64748B)),
                  SizedBox(height: 12),
                  Text('No completed orders yet.',
                      style: TextStyle(color: const Color(0xFF64748B))),
                ],
              ),
            ),
          )
        else
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: grouped.length,
              itemBuilder: (context, index) {
                final entry = grouped[index];
                return _LedgerGroupCard(
                  label: entry.label,
                  orders: entry.orders,
                  total: entry.total,
                );
              },
            ),
          ),
      ],
    );
  }

  List<_LedgerGroup> _groupOrders(List<Order> orders, LedgerPeriod period) {
    final Map<String, List<Order>> map = {};

    for (final order in orders) {
      final dt = DateTime.parse(order.createdAt);
      final key = switch (period) {
        LedgerPeriod.daily => _dayKey(dt),
        LedgerPeriod.weekly => _weekKey(dt),
        LedgerPeriod.monthly => _monthKey(dt),
      };
      map.putIfAbsent(key, () => []).add(order);
    }

    final groups = map.entries.map((e) {
      final total = e.value.fold<double>(0, (s, o) => s + o.totalAmount);
      return _LedgerGroup(label: e.key, orders: e.value, total: total);
    }).toList();

    // Sort newest first
    groups.sort((a, b) => b.label.compareTo(a.label));
    return groups;
  }

  String _dayKey(DateTime dt) =>
      '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';

  String _weekKey(DateTime dt) {
    // ISO week: Monday start
    final monday = dt.subtract(Duration(days: dt.weekday - 1));
    final sunday = monday.add(const Duration(days: 6));
    return '${_fmt(monday)} – ${_fmt(sunday)}';
  }

  String _monthKey(DateTime dt) {
    const months = [
      '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    return '${months[dt.month]} ${dt.year}';
  }

  String _fmt(DateTime dt) =>
      '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}';
}

class _LedgerGroup {
  final String label;
  final List<Order> orders;
  final double total;
  const _LedgerGroup(
      {required this.label, required this.orders, required this.total});
}

class _LedgerGroupCard extends StatelessWidget {
  final String label;
  final List<Order> orders;
  final double total;

  const _LedgerGroupCard(
      {required this.label, required this.orders, required this.total});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        title: Text(label,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
        subtitle: Text(
          '${orders.length} order${orders.length == 1 ? '' : 's'}',
          style: const TextStyle(color: const Color(0xFF64748B), fontSize: 12),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '₹${total.toStringAsFixed(2)}',
              style: const TextStyle(
                  color: const Color(0xFFFF5722),
                  fontWeight: FontWeight.bold,
                  fontSize: 16),
            ),
            const SizedBox(width: 4),
            const Icon(Icons.expand_more),
          ],
        ),
        children: orders.map((o) => _OrderRow(order: o)).toList(),
      ),
    );
  }
}

class _OrderRow extends StatelessWidget {
  final Order order;
  const _OrderRow({required this.order});

  @override
  Widget build(BuildContext context) {
    final dt = DateTime.parse(order.createdAt);
    final timeStr =
        '${dt.hour > 12 ? dt.hour - 12 : dt.hour}:${dt.minute.toString().padLeft(2, '0')} ${dt.hour >= 12 ? 'PM' : 'AM'}';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          const Icon(Icons.receipt, size: 16, color: const Color(0xFF64748B)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Order #${order.id} · $timeStr · ${order.paymentMode}',
              style: const TextStyle(fontSize: 13, color: const Color(0xFF1E293B)),
            ),
          ),
          Text(
            '₹${order.totalAmount.toStringAsFixed(2)}',
            style: const TextStyle(
                fontWeight: FontWeight.w600, fontSize: 13),
          ),
        ],
      ),
    );
  }
}