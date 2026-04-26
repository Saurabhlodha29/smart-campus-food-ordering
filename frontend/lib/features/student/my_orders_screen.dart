// lib/features/student/my_orders_screen.dart

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/order_model.dart';
import '../../core/theme/app_theme.dart';
import 'student_provider.dart';

class MyOrdersScreen extends ConsumerWidget {
  const MyOrdersScreen({super.key});

  Color _statusColor(String status) => switch (status) {
        'PLACED' => Colors.blue,
        'PREPARING' => Colors.orange,
        'READY' => Colors.green,
        'PICKED' => Colors.grey,
        'EXPIRED' => Colors.red,
        _ => Colors.grey,
      };

  IconData _statusIcon(String status) => switch (status) {
        'PLACED' => Icons.receipt_long,
        'PREPARING' => Icons.soup_kitchen,
        'READY' => Icons.check_circle,
        'PICKED' => Icons.done_all,
        'EXPIRED' => Icons.cancel,
        _ => Icons.help_outline,
      };

  String _formatTime(DateTime dt) {
    final hour = dt.hour > 12 ? dt.hour - 12 : dt.hour;
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    final min = dt.minute.toString().padLeft(2, '0');
    return '$hour:$min $period';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(myOrdersProvider);

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('My Orders'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(myOrdersProvider),
          ),
        ],
      ),
      body: ordersAsync.when(
        data: (orders) {
          if (orders.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.receipt_long_outlined,
                      size: 80, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No orders yet!',
                      style: TextStyle(fontSize: 18, color: Colors.grey)),
                  SizedBox(height: 8),
                  Text('Order something from the home screen.',
                      style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          // Sort newest first
          final sorted = [...orders]
            ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(myOrdersProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: sorted.length,
              itemBuilder: (context, index) {
                final order = sorted[index];
                return _OrderCard(
                  order: order,
                  statusColor: _statusColor(order.status),
                  statusIcon: _statusIcon(order.status),
                  formatTime: _formatTime,
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 12),
              Text('$err', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => ref.invalidate(myOrdersProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// ORDER CARD — has its own timer for READY orders
// ---------------------------------------------------------------------------

class _OrderCard extends StatefulWidget {
  final Order order;
  final Color statusColor;
  final IconData statusIcon;
  final String Function(DateTime) formatTime;

  const _OrderCard({
    required this.order,
    required this.statusColor,
    required this.statusIcon,
    required this.formatTime,
  });

  @override
  State<_OrderCard> createState() => _OrderCardState();
}

class _OrderCardState extends State<_OrderCard> {
  Timer? _timer;
  Duration _remaining = Duration.zero;

  @override
  void initState() {
    super.initState();
    if (widget.order.status == 'READY') {
      _startTimer();
    }
  }

  void _startTimer() {
    _updateRemaining();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateRemaining();
    });
  }

  void _updateRemaining() {
    final remaining =
        widget.order.expiresAtDate.difference(DateTime.now());
    if (remaining.isNegative) {
      _timer?.cancel();
      setState(() => _remaining = Duration.zero);
    } else {
      setState(() => _remaining = remaining);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Color _countdownColor() {
    final minutes = _remaining.inMinutes;
    if (minutes > 10) return Colors.green;
    if (minutes >= 5) return Colors.orange;
    return Colors.red;
  }

  String _formatDuration(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final order = widget.order;
    final isReady = order.status == 'READY';
    final countdownColor = _countdownColor();

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: AppTheme.softShadows,
        border: isReady ? Border.all(color: countdownColor, width: 1.5) : Border.all(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: widget.statusColor.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(widget.statusIcon, color: widget.statusColor, size: 20),
                ),
                const SizedBox(width: 12),
                Text('Order #${order.id}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: widget.statusColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    order.status,
                    style: TextStyle(
                        color: widget.statusColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 12),

            // Amount + payment
            Row(
              children: [
                Text('₹${order.totalAmount.toStringAsFixed(2)}',
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.text)),
                const SizedBox(width: 12),
                Text('• ${order.paymentMode}',
                    style: TextStyle(color: Colors.grey.shade600)),
                const SizedBox(width: 8),
                Text('• ${order.paymentStatus}',
                    style: TextStyle(
                        color: order.paymentStatus == 'PAID'
                            ? Colors.green
                            : Colors.orange,
                        fontWeight: FontWeight.w600)),
              ],
            ),

            const SizedBox(height: 8),

            // Ready time
            Row(
              children: [
                const Icon(Icons.access_time, size: 16, color: Colors.grey),
                const SizedBox(width: 6),
                Text(
                  'Ready by ${widget.formatTime(order.readyAtDate)}',
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),
              ],
            ),

            // COUNTDOWN — only for READY orders
            if (isReady) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: countdownColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: countdownColor.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.timer, color: countdownColor, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '🍽️ Your food is ready! Pick it up!',
                            style: TextStyle(
                                color: countdownColor,
                                fontWeight: FontWeight.bold,
                                fontSize: 13),
                          ),
                          Text(
                            _remaining == Duration.zero
                                ? 'Time expired!'
                                : 'Expires in ${_formatDuration(_remaining)}',
                            style: TextStyle(
                                color: countdownColor, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}