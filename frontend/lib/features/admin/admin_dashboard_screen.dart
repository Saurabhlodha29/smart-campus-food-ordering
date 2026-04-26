// lib/features/admin/admin_dashboard_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/storage/secure_storage.dart';
import 'admin_provider.dart';

class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    await StorageService.clearAll();
    if (context.mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pendingAsync = ref.watch(pendingOutletAppsProvider);
    final outletsAsync = ref.watch(campusOutletsAdminProvider);

    final pendingCount = pendingAsync.when(
      data: (list) => list.length,
      loading: () => 0,
      error: (_, __) => 0,
    );
    final outletCount = outletsAsync.when(
      data: (list) => list.length,
      loading: () => 0,
      error: (_, __) => 0,
    );
    final activeCount = outletsAsync.when(
      data: (list) => list.where((o) => o.status == 'ACTIVE').length,
      loading: () => 0,
      error: (_, __) => 0,
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Campus Admin Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () => context.push('/admin/notifications'),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => _logout(context),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(pendingOutletAppsProvider);
          ref.invalidate(campusOutletsAdminProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Summary cards row
            Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    label: 'Total Outlets',
                    value: '$outletCount',
                    icon: Icons.storefront,
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _SummaryCard(
                    label: 'Active',
                    value: '$activeCount',
                    icon: Icons.check_circle,
                    color: Colors.green,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _SummaryCard(
                    label: 'Pending Apps',
                    value: '$pendingCount',
                    icon: Icons.pending_actions,
                    color: pendingCount > 0 ? Colors.orange : Colors.grey,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),
            const Text('Quick Actions',
                style:
                    TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),

            // Action tiles
            _ActionTile(
              icon: Icons.rate_review,
              color: Colors.orange,
              title: 'Review Outlet Applications',
              subtitle: pendingCount > 0
                  ? '$pendingCount pending application${pendingCount > 1 ? 's' : ''}'
                  : 'No pending applications',
              onTap: () => context.go('/admin/outlet-apps'),
              badge: pendingCount,
            ),
            const SizedBox(height: 10),
            _ActionTile(
              icon: Icons.storefront,
              color: Colors.blue,
              title: 'Manage Outlets',
              subtitle: 'Suspend or reactivate campus outlets',
              onTap: () => context.go('/admin/outlets'),
            ),
            const SizedBox(height: 10),
            _ActionTile(
              icon: Icons.history,
              color: Colors.grey,
              title: 'Application History',
              subtitle: 'View all past outlet applications',
              onTap: () => context.go('/admin/outlet-history'),
            ),
            const SizedBox(height: 10),
            _ActionTile(
              icon: Icons.gavel,
              color: Colors.red,
              title: 'Penalty Management',
              subtitle: 'Search students and waive penalties',
              onTap: () => context.go('/admin/penalties'),
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 6),
          Text(value,
              style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: color)),
          Text(label,
              style: const TextStyle(fontSize: 11, color: Colors.grey),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final int badge;

  const _ActionTile({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.badge = 0,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: color),
        ),
        title: Text(title,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle,
            style: const TextStyle(fontSize: 12)),
        trailing: badge > 0
            ? Container(
                padding: const EdgeInsets.all(6),
                decoration: const BoxDecoration(
                    color: Colors.orange, shape: BoxShape.circle),
                child: Text('$badge',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold)),
              )
            : const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}