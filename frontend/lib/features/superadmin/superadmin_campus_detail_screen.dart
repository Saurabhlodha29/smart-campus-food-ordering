// lib/features/superadmin/superadmin_campus_detail_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'superadmin_provider.dart';

class SuperAdminCampusDetailScreen extends ConsumerWidget {
  final int campusId;
  const SuperAdminCampusDetailScreen({super.key, required this.campusId});

  Future<void> _confirmDelete(
      BuildContext context, WidgetRef ref, String campusName) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete Campus?',
            style: TextStyle(color: const Color(0xFFEF4444))),
        content: Text(
          'This will permanently delete "$campusName" and all associated data. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('DELETE PERMANENTLY'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref.read(superAdminProvider.notifier).deleteCampus(campusId);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Campus "$campusName" deleted.'),
              backgroundColor: const Color(0xFFEF4444),
            ),
          );
          Navigator.pop(context); // go back to campus list
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
                content: Text('Delete failed: $e'),
                backgroundColor: const Color(0xFFEF4444)),
          );
        }
      }
    }
  }

  Future<void> _confirmToggle(BuildContext context, WidgetRef ref,
      bool currentlyActive) async {
    final action = currentlyActive ? 'deactivate' : 'reactivate';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('${action[0].toUpperCase()}${action.substring(1)} campus?'),
        content: Text(
          currentlyActive
              ? 'This will disable the campus. Students will be unable to log in or order.'
              : 'This will restore the campus to active status.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: currentlyActive ? const Color(0xFFEF4444) : const Color(0xFF10B981),
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: Text(action.toUpperCase()),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        if (currentlyActive) {
          await ref.read(superAdminProvider.notifier).deactivateCampus(campusId);
        } else {
          await ref.read(superAdminProvider.notifier).reactivateCampus(campusId);
        }
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                  'Campus ${currentlyActive ? 'deactivated' : 'reactivated'} successfully.'),
              backgroundColor: currentlyActive ? const Color(0xFFEF4444) : const Color(0xFF10B981),
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
                content: Text('Action failed: $e'),
                backgroundColor: const Color(0xFFEF4444)),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final campusAsync = ref.watch(campusDetailProvider(campusId));
    final outletsAsync = ref.watch(campusOutletsProvider(campusId));

    return Scaffold(
      appBar: AppBar(
        title: campusAsync.when(
          data: (c) => Text(c.name),
          loading: () => const Text('Campus Detail'),
          error: (_, __) => const Text('Campus Detail'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(campusDetailProvider(campusId));
              ref.invalidate(campusOutletsProvider(campusId));
            },
          ),
        ],
      ),
      body: campusAsync.when(
        data: (campus) {
          final isActive = campus.status == 'ACTIVE';
          final statusColor = isActive ? const Color(0xFF10B981) : const Color(0xFFEF4444);

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(campusDetailProvider(campusId));
              ref.invalidate(campusOutletsProvider(campusId));
            },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Campus info card
                Card(
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16)),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              radius: 28,
                              backgroundColor: statusColor.withOpacity(0.15),
                              child: Icon(Icons.account_balance,
                                  color: statusColor, size: 28),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(campus.name,
                                      style: const TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold)),
                                  const SizedBox(height: 2),
                                  Text(campus.location,
                                      style: const TextStyle(
                                          color: const Color(0xFF64748B), fontSize: 13)),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        _InfoRow(
                            icon: Icons.email_outlined,
                            label: 'Email Domain',
                            value: '@${campus.emailDomain}'),
                        _InfoRow(
                            icon: Icons.circle,
                            label: 'Status',
                            value: campus.status,
                            valueColor: statusColor),
                        _InfoRow(
                            icon: Icons.calendar_today_outlined,
                            label: 'Created',
                            value: campus.createdAt.split('T').first),
                        const SizedBox(height: 20),
                        // Deactivate / Reactivate button
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor:
                                  isActive ? const Color(0xFFEF4444) : const Color(0xFF10B981),
                              foregroundColor: Colors.white,
                              padding:
                                  const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10)),
                            ),
                            icon: Icon(
                                isActive ? Icons.block : Icons.check_circle),
                            label: Text(
                              isActive
                                  ? 'Deactivate Campus'
                                  : 'Reactivate Campus',
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 15),
                            ),
                            onPressed: () =>
                                _confirmToggle(context, ref, isActive),
                          ),
                        ),
                        const SizedBox(height: 10),
                        // Delete campus button
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: const Color(0xFFEF4444)),
                              padding:
                                  const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10)),
                            ),
                            icon: const Icon(Icons.delete_forever,
                                color: const Color(0xFFEF4444)),
                            label: const Text('Delete Campus',
                                style: TextStyle(
                                    color: const Color(0xFFEF4444),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 15)),
                            onPressed: () =>
                                _confirmDelete(context, ref, campus.name),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 20),

                // Outlets section
                Row(
                  children: [
                    const Text('Outlets on this Campus',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
                    const Spacer(),
                    outletsAsync.when(
                      data: (outlets) => Text('${outlets.length} total',
                          style: const TextStyle(color: const Color(0xFF64748B))),
                      loading: () => const SizedBox.shrink(),
                      error: (_, __) => const SizedBox.shrink(),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                outletsAsync.when(
                  data: (outlets) {
                    if (outlets.isEmpty) {
                      return Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: Colors.grey[100],
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Center(
                          child: Text('No outlets on this campus yet.',
                              style: TextStyle(color: const Color(0xFF64748B))),
                        ),
                      );
                    }
                    return Column(
                      children: outlets
                          .map((outlet) => _OutletRow(outlet: outlet))
                          .toList(),
                    );
                  },
                  loading: () => const Center(
                      child: Padding(
                    padding: EdgeInsets.all(24),
                    child: CircularProgressIndicator(),
                  )),
                  error: (e, _) => Center(child: Text('Error: $e')),
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
              const Icon(Icons.error_outline, size: 48, color: const Color(0xFFEF4444)),
              const SizedBox(height: 12),
              Text('$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () =>
                    ref.invalidate(campusDetailProvider(campusId)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Icon(icon, size: 16, color: const Color(0xFF64748B)),
          const SizedBox(width: 8),
          Text('$label: ',
              style: const TextStyle(color: const Color(0xFF64748B), fontSize: 13)),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: valueColor ?? Colors.black87,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OutletRow extends StatelessWidget {
  final dynamic outlet;
  const _OutletRow({required this.outlet});

  Color _statusColor(String status) => switch (status) {
        'ACTIVE' => const Color(0xFF10B981),
        'CLOSED' => const Color(0xFF0EA5E9),
        'SUSPENDED' => const Color(0xFFEF4444),
        'PENDING_LAUNCH' => Colors.amber,
        _ => const Color(0xFF64748B),
      };

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(outlet.status);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.12),
          child: Icon(Icons.storefront, color: color, size: 20),
        ),
        title: Text(outlet.name,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('~${outlet.avgPrepTime} min prep',
            style: const TextStyle(fontSize: 12)),
        trailing: Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: color.withOpacity(0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(outlet.status,
              style: TextStyle(
                  color: color,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
        ),
      ),
    );
  }
}