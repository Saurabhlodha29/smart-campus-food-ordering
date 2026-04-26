// lib/features/student/penalty_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/api/api_client.dart';

// ---------------------------------------------------------------------------
// PROVIDER
// ---------------------------------------------------------------------------

final penaltyStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  final userId = prefs.getString('userId') ?? '';
  if (userId.isEmpty) throw Exception('User ID not found');
  final response = await ApiClient.dio.get('/api/penalties/$userId/status');
  return Map<String, dynamic>.from(response.data);
});

// ---------------------------------------------------------------------------
// SCREEN
// ---------------------------------------------------------------------------

class PenaltyScreen extends ConsumerStatefulWidget {
  const PenaltyScreen({super.key});

  @override
  ConsumerState<PenaltyScreen> createState() => _PenaltyScreenState();
}

class _PenaltyScreenState extends ConsumerState<PenaltyScreen> {
  bool _paying = false;

  Future<void> _payPenalty() async {
    setState(() => _paying = true);
    try {
      final prefs = await SharedPreferences.getInstance();
      final userId = prefs.getString('userId') ?? '';

      await ApiClient.dio.post('/api/penalties/$userId/pay', data: {
        'paymentMode': 'ONLINE',
      });

      // Update local accountStatus so home screen banner disappears
      await prefs.setString('accountStatus', 'ACTIVE');
      await prefs.setString('pendingPenalty', '0.0');

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Penalty paid! Your account is restored.'),
            backgroundColor: Colors.green,
          ),
        );
        ref.invalidate(penaltyStatusProvider);
        context.go('/student/home');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Payment failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _paying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final penaltyAsync = ref.watch(penaltyStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Penalty Details'),
      ),
      body: penaltyAsync.when(
        data: (data) {
          final pendingPenalty =
              double.tryParse(data['pendingPenalty']?.toString() ?? '0') ?? 0.0;
          final noShowCount =
              int.tryParse(data['noShowCount']?.toString() ?? '0') ?? 0;
          final accountStatus = data['accountStatus']?.toString() ?? '';
          final hasPenalty = pendingPenalty > 0;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Status icon
                Center(
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: hasPenalty
                          ? Colors.red[50]
                          : Colors.green[50],
                    ),
                    child: Icon(
                      hasPenalty ? Icons.warning_amber_rounded : Icons.check_circle,
                      size: 64,
                      color: hasPenalty ? Colors.red : Colors.green,
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                Center(
                  child: Text(
                    hasPenalty ? 'Outstanding Penalty' : 'No Pending Penalty',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: hasPenalty ? Colors.red : Colors.green,
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // Details card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        _DetailRow(
                          icon: Icons.account_circle_outlined,
                          label: 'Account Status',
                          value: accountStatus,
                          valueColor: accountStatus == 'ACTIVE'
                              ? Colors.green
                              : Colors.orange,
                        ),
                        const Divider(height: 24),
                        _DetailRow(
                          icon: Icons.block,
                          label: 'No-Show Count',
                          value: '$noShowCount time${noShowCount != 1 ? 's' : ''}',
                          valueColor:
                              noShowCount >= 3 ? Colors.red : Colors.black87,
                        ),
                        const Divider(height: 24),
                        _DetailRow(
                          icon: Icons.currency_rupee,
                          label: 'Pending Amount',
                          value: '₹${pendingPenalty.toStringAsFixed(2)}',
                          valueColor:
                              hasPenalty ? Colors.red : Colors.green,
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 24),

                // Info box
                if (hasPenalty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.orange[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange[200]!),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.info_outline,
                            color: Colors.orange, size: 18),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'You must pay this penalty before you can place new orders. '
                            'Penalties are charged when you don\'t pick up a READY order within 30 minutes.',
                            style:
                                TextStyle(color: Colors.orange, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),

                if (!hasPenalty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.green[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.green[200]!),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.check_circle_outline,
                            color: Colors.green, size: 18),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Your account is in good standing. Keep picking up your orders on time!',
                            style:
                                TextStyle(color: Colors.green, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),

                const SizedBox(height: 32),

                // Pay button — only shown if penalty exists
                if (hasPenalty)
                  ElevatedButton.icon(
                    onPressed: _paying ? null : _payPenalty,
                    icon: _paying
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2))
                        : const Icon(Icons.payment),
                    label: Text(
                      _paying
                          ? 'Processing...'
                          : 'Pay ₹${pendingPenalty.toStringAsFixed(2)} Now',
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.deepOrange,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      textStyle: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),

                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context.go('/student/home'),
                  child: const Text('Back to Home'),
                ),
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
                onPressed: () => ref.invalidate(penaltyStatusProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: Colors.grey, size: 20),
        const SizedBox(width: 12),
        Expanded(
          child: Text(label,
              style: const TextStyle(color: Colors.grey)),
        ),
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: valueColor ?? Colors.black87,
          ),
        ),
      ],
    );
  }
}