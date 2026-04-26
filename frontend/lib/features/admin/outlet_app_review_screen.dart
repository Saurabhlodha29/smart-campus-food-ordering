// lib/features/admin/outlet_app_review_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/outlet_application_model.dart';
import 'admin_provider.dart';

class OutletAppReviewScreen extends ConsumerWidget {
  const OutletAppReviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appsAsync = ref.watch(pendingOutletAppsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Outlet Applications'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/admin/dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(pendingOutletAppsProvider),
          ),
        ],
      ),
      body: appsAsync.when(
        data: (apps) => apps.isEmpty
            ? const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle_outline,
                        size: 64, color: Colors.green),
                    SizedBox(height: 16),
                    Text('No pending applications!',
                        style: TextStyle(fontSize: 18, color: Colors.grey)),
                  ],
                ),
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: apps.length,
                itemBuilder: (context, index) =>
                    _OutletAppCard(app: apps[index]),
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _OutletAppCard extends ConsumerWidget {
  final OutletApplication app;
  const _OutletAppCard({required this.app});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.storefront, color: Colors.deepOrange),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(app.outletName,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                ),
                // Attempt badge
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: app.attemptNumber >= 3
                        ? Colors.red[100]
                        : Colors.orange[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    'Attempt ${app.attemptNumber}/3',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: app.attemptNumber >= 3
                          ? Colors.red[800]
                          : Colors.orange[800],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Manager details
            _DetailRow(
                icon: Icons.person_outline,
                text: app.managerName),
            _DetailRow(
                icon: Icons.email_outlined,
                text: app.managerEmail),
            _DetailRow(
                icon: Icons.timer_outlined,
                text: '~${app.avgPrepTime} min avg prep time'),

            if (app.outletDescription != null &&
                app.outletDescription!.isNotEmpty)
              _DetailRow(
                  icon: Icons.description_outlined,
                  text: app.outletDescription!),

            // License document link
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                      content: Text('License URL: ${app.licenseDocUrl}')),
                );
              },
              child: Row(
                children: [
                  const Icon(Icons.link, size: 16, color: Colors.blue),
                  const SizedBox(width: 6),
                  const Text('View License Document',
                      style: TextStyle(
                          color: Colors.blue,
                          decoration: TextDecoration.underline,
                          fontSize: 13)),
                ],
              ),
            ),

            const SizedBox(height: 16),
            const Divider(),

            // Action buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.close, color: Colors.red),
                    label: const Text('Reject',
                        style: TextStyle(color: Colors.red)),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.red),
                    ),
                    onPressed: () => _showRejectDialog(context, ref),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.check),
                    label: const Text('Approve'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () => _showApproveDialog(context, ref),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showApproveDialog(BuildContext context, WidgetRef ref) {
    final passCtrl = TextEditingController(text: 'Welcome@123');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24, right: 24, top: 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Approve "${app.outletName}"?',
                style: const TextStyle(
                    fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('Manager: ${app.managerName} (${app.managerEmail})',
                style: const TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 16),
            TextField(
              controller: passCtrl,
              decoration: const InputDecoration(
                labelText: 'Temporary Password for Manager',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lock_outline),
                helperText: 'Manager will use this to log in for the first time',
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
                    .read(adminProvider.notifier)
                    .approveOutletApp(app.id, passCtrl.text);
                if (ctx.mounted) Navigator.pop(ctx);
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(
                      content: Text(
                          '✅ "${app.outletName}" approved! Manager account created.'),
                      backgroundColor: Colors.green,
                    ),
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

  void _showRejectDialog(BuildContext context, WidgetRef ref) {
    final reasonCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
          left: 24, right: 24, top: 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Reject "${app.outletName}"?',
                style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.red)),
            const SizedBox(height: 4),
            Text(
              app.attemptNumber >= 3
                  ? '⚠️ This is their final attempt. Rejection is permanent.'
                  : '${3 - app.attemptNumber} attempt(s) remaining after this.',
              style: TextStyle(
                color: app.attemptNumber >= 3 ? Colors.red : Colors.orange,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: reasonCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Reason for rejection',
                border: OutlineInputBorder(),
                hintText:
                    'e.g. Invalid license, incomplete details...',
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
                if (reasonCtrl.text.trim().isEmpty) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    const SnackBar(
                        content: Text('Please provide a rejection reason')),
                  );
                  return;
                }
                await ref
                    .read(adminProvider.notifier)
                    .rejectOutletApp(app.id, reasonCtrl.text.trim());
                if (ctx.mounted) Navigator.pop(ctx);
                if (ctx.mounted) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(
                        content: Text(
                            '❌ "${app.outletName}" application rejected.')),
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

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String text;
  const _DetailRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text,
                  style: const TextStyle(color: Colors.black87))),
        ],
      ),
    );
  }
}