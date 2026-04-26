// lib/features/student/order_confirmation_screen.dart

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/order_model.dart';

class OrderConfirmationScreen extends StatefulWidget {
  final Order order;
  const OrderConfirmationScreen({super.key, required this.order});

  @override
  State<OrderConfirmationScreen> createState() =>
      _OrderConfirmationScreenState();
}

class _OrderConfirmationScreenState extends State<OrderConfirmationScreen> {
  Timer? _timer;
  Duration _remaining = Duration.zero;
  bool _isWaitingForReady = true; // true = counting to readyAt, false = counting to expiresAt

  @override
  void initState() {
    super.initState();
    _startCountdown();
  }

  void _startCountdown() {
    _updateRemaining();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateRemaining();
    });
  }

  void _updateRemaining() {
    final now = DateTime.now();
    final readyAt = widget.order.readyAtDate;
    final expiresAt = widget.order.expiresAtDate;

    if (now.isBefore(readyAt)) {
      // Food not ready yet — count down to readyAt
      setState(() {
        _isWaitingForReady = true;
        _remaining = readyAt.difference(now);
      });
    } else {
      // Food is ready — count down to expiry
      final remaining = expiresAt.difference(now);
      if (remaining.isNegative) {
        _timer?.cancel();
        setState(() {
          _isWaitingForReady = false;
          _remaining = Duration.zero;
        });
      } else {
        setState(() {
          _isWaitingForReady = false;
          _remaining = remaining;
        });
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Color _countdownColor() {
    if (_isWaitingForReady) return Colors.deepOrange;
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

  String _formatTime(DateTime dt) {
    final hour = dt.hour == 0 ? 12 : (dt.hour > 12 ? dt.hour - 12 : dt.hour);
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    final min = dt.minute.toString().padLeft(2, '0');
    return '$hour:$min $period';
  }

  @override
  Widget build(BuildContext context) {
    final order = widget.order;
    final color = _countdownColor();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Order Confirmed!'),
        automaticallyImplyLeading: false,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            // Success icon
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.green[50],
              ),
              child: const Icon(Icons.check_circle, color: Colors.green, size: 80),
            ),
            const SizedBox(height: 16),
            const Text('Your order is placed!',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('Order #${order.id}',
                style: const TextStyle(color: Colors.grey)),

            const SizedBox(height: 32),

            // Ready by card
            _InfoCard(
              icon: Icons.access_time_filled,
              iconColor: Colors.deepOrange,
              label: 'Ready by',
              value: _formatTime(order.readyAtDate),
              valueStyle: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.deepOrange),
            ),

            const SizedBox(height: 16),

            // Smart countdown card
            _InfoCard(
              icon: _isWaitingForReady ? Icons.soup_kitchen : Icons.hourglass_bottom,
              iconColor: color,
              label: _isWaitingForReady ? 'Food ready in' : 'Pick up within',
              value: _remaining == Duration.zero && !_isWaitingForReady
                  ? 'Expired!'
                  : _formatDuration(_remaining),
              valueStyle: TextStyle(
                  fontSize: 28, fontWeight: FontWeight.bold, color: color),
              subtitle: _isWaitingForReady
                  ? 'Head to the outlet around ${_formatTime(order.readyAtDate)}'
                  : 'Expires at ${_formatTime(order.expiresAtDate)} — late pickup = penalty',
            ),

            const SizedBox(height: 16),

            // Payment info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _DetailRow('Total Amount',
                        '₹${order.totalAmount.toStringAsFixed(2)}'),
                    const Divider(),
                    _DetailRow('Payment Mode', order.paymentMode),
                    const Divider(),
                    _DetailRow('Payment Status', order.paymentStatus),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 32),

            ElevatedButton.icon(
              onPressed: () => context.go('/student/orders'),
              icon: const Icon(Icons.receipt_long),
              label: const Text('View My Orders'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.deepOrange,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              ),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => context.go('/student/home'),
              child: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final TextStyle valueStyle;
  final String? subtitle;

  const _InfoCard({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.valueStyle,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(icon, color: iconColor, size: 32),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(color: Colors.grey, fontSize: 13)),
                  Text(value, style: valueStyle),
                  if (subtitle != null) ...[
                    const SizedBox(height: 4),
                    Text(subtitle!,
                        style: const TextStyle(color: Colors.grey, fontSize: 11)),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  const _DetailRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}