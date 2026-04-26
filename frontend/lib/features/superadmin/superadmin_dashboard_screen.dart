// lib/features/superadmin/superadmin_dashboard_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/models/admin_application_model.dart';
import 'superadmin_provider.dart';

class SuperAdminDashboardScreen extends ConsumerWidget {
  const SuperAdminDashboardScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    await StorageService.clearAll(); // Now correctly wipes everything
    if (context.mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('SuperAdmin Dashboard'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Pending', icon: Icon(Icons.pending_actions)),
              Tab(text: 'All Applications', icon: Icon(Icons.history)),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => ref.invalidate(pendingAdminAppsProvider),
            ),
            IconButton(
              icon: const Icon(Icons.logout),
              onPressed: () => _logout(context),
            ),
          ],
        ),
        body: TabBarView(
          children: [
            _PendingList(),
            _AllApplicationsList(),
          ],
        ),
      ),
    );
  }
}

// --- PENDING TAB ---
class _PendingList extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appsAsync = ref.watch(pendingAdminAppsProvider);

    return appsAsync.when(
      data: (apps) => apps.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_outline, size: 64, color: Colors.green),
                  SizedBox(height: 16),
                  Text('No pending applications!',
                      style: TextStyle(fontSize: 18, color: Colors.grey)),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: apps.length,
              itemBuilder: (context, index) {
                final app = apps[index];
                return _ApplicationCard(app: app);
              },
            ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text('Error loading applications\n$err',
                textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

// --- APPLICATION CARD WIDGET ---
class _ApplicationCard extends ConsumerWidget {
  final AdminApplication app;
  const _ApplicationCard({required this.app});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                const Icon(Icons.account_balance, color: Colors.deepOrange),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    app.campusName,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
                // Attempt badge — max 3 attempts
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: app.attemptNumber >= 3
                        ? Colors.red[100]
                        : Colors.orange[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    'Attempt ${app.attemptNumber}/3',
                    style: TextStyle(
                      fontSize: 12,
                      color: app.attemptNumber >= 3
                          ? Colors.red[800]
                          : Colors.orange[800],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('Applicant: ${app.fullName}',
                style: const TextStyle(color: Colors.black87)),
            Text('Email: ${app.applicantEmail}',
                style: const TextStyle(color: Colors.grey)),
            Text('Designation: ${app.designation}',
                style: const TextStyle(color: Colors.grey)),
            Text('Domain: ${app.campusEmailDomain}',
                style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 12),
            const Divider(),
            // Action buttons row
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                // BUG FIX: Reject button was missing from the UI entirely
                OutlinedButton.icon(
                  icon: const Icon(Icons.close, color: Colors.red),
                  label:
                      const Text('Reject', style: TextStyle(color: Colors.red)),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.red),
                  ),
                  onPressed: () => _showRejectDialog(context, ref, app),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  icon: const Icon(Icons.check),
                  label: const Text('Approve'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () => _showApproveDialog(context, ref, app),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // --- APPROVE DIALOG ---
  void _showApproveDialog(
      BuildContext context, WidgetRef ref, AdminApplication app) {
    final passController = TextEditingController(text: 'Welcome@123');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24,
          right: 24,
          top: 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Approve ${app.fullName}?',
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text('Campus: ${app.campusName}',
                style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 16),
            TextField(
              controller: passController,
              decoration: const InputDecoration(
                labelText: 'Temporary Password',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lock_outline),
                helperText: 'Admin will be asked to change this on first login',
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              onPressed: () async {
                await ref
                    .read(superAdminProvider.notifier)
                    .approveApplication(app.id, passController.text);
                if (ctx.mounted) Navigator.pop(ctx);
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(
                        content: Text(
                            '✅ ${app.fullName} approved as Campus Admin!')),
                  );
                }
              },
              child: const Text('CONFIRM APPROVAL',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // --- REJECT DIALOG (BUG FIX: was completely missing from UI) ---
  void _showRejectDialog(
      BuildContext context, WidgetRef ref, AdminApplication app) {
    final reasonController = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24,
          right: 24,
          top: 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Reject ${app.fullName}?',
              style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.red),
            ),
            const SizedBox(height: 4),
            Text(
              app.attemptNumber >= 3
                  ? '⚠️ This is their final attempt (3/3). Rejection is permanent.'
                  : 'They have ${3 - app.attemptNumber} attempt(s) remaining after this.',
              style: TextStyle(
                color: app.attemptNumber >= 3 ? Colors.red : Colors.orange,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Reason for rejection',
                border: OutlineInputBorder(),
                hintText: 'e.g. Incomplete documentation, invalid domain...',
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              onPressed: () async {
                if (reasonController.text.trim().isEmpty) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(
                        content: Text('Please provide a rejection reason')),
                  );
                  return;
                }
                await ref
                    .read(superAdminProvider.notifier)
                    .rejectApplication(app.id, reasonController.text.trim());
                if (ctx.mounted) Navigator.pop(ctx);
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(
                        content:
                            Text('❌ ${app.fullName}\'s application rejected.')),
                  );
                }
              },
              child: const Text('CONFIRM REJECTION',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

// --- ALL APPLICATIONS TAB (placeholder for history) ---
class _AllApplicationsList extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appsAsync = ref.watch(allAdminAppsProvider);

    return appsAsync.when(
      data: (apps) => apps.isEmpty
          ? const Center(child: Text('No applications yet.'))
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: apps.length,
              itemBuilder: (context, index) {
                final app = apps[index];
                final statusColor = switch (app.status) {
                  'APPROVED' => Colors.green,
                  'REJECTED' => Colors.red,
                  _ => Colors.orange,
                };
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(app.campusName),
                    subtitle: Text(app.fullName),
                    trailing: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        app.status,
                        style: TextStyle(
                            color: statusColor, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                );
              },
            ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text('Error: $err')),
    );
  }
}