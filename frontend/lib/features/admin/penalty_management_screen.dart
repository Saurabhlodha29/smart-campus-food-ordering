// lib/features/admin/penalty_management_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'admin_provider.dart';

class PenaltyManagementScreen extends ConsumerStatefulWidget {
  const PenaltyManagementScreen({super.key});

  @override
  ConsumerState<PenaltyManagementScreen> createState() =>
      _PenaltyManagementScreenState();
}

class _PenaltyManagementScreenState
    extends ConsumerState<PenaltyManagementScreen> {
  final _searchCtrl = TextEditingController();
  bool _isLoading = false;
  Map<String, dynamic>? _penaltyData;
  String? _searchedId;
  String? _error;

  Future<void> _search() async {
    final id = _searchCtrl.text.trim();
    if (id.isEmpty) return;
    setState(() {
      _isLoading = true;
      _penaltyData = null;
      _error = null;
      _searchedId = id;
    });
    try {
      final data =
          await ref.read(adminProvider.notifier).getPenaltyStatus(id);
      setState(() {
        _penaltyData = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Student not found or error: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _waive() async {
    if (_searchedId == null) return;
    try {
      await ref.read(adminProvider.notifier).waivePenalty(_searchedId!);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Penalty waived successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        setState(() => _penaltyData = null);
        _searchCtrl.clear();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to waive: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Penalty Management'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/admin/dashboard'),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Search bar
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Enter Student ID',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.search),
                      hintText: 'e.g. 42',
                    ),
                    keyboardType: TextInputType.number,
                    onSubmitted: (_) => _search(),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _search,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepOrange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 16),
                  ),
                  child: const Text('Search'),
                ),
              ],
            ),

            const SizedBox(height: 24),

            if (_isLoading)
              const Center(child: CircularProgressIndicator()),

            if (_error != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red[200]!),
                ),
                child: Text(_error!,
                    style: const TextStyle(color: Colors.red)),
              ),

            if (_penaltyData != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Student ID: $_searchedId',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      const Divider(height: 24),
                      _InfoRow('Account Status',
                          '${_penaltyData!['accountStatus']}'),
                      _InfoRow('No-Show Count',
                          '${_penaltyData!['noShowCount']}'),
                      _InfoRow('Pending Penalty',
                          '₹${_penaltyData!['pendingPenalty']}'),
                      const SizedBox(height: 16),
                      if ((_penaltyData!['pendingPenalty'] ?? 0) > 0)
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.gavel),
                            label: const Text('Waive Penalty'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(
                                  vertical: 14),
                            ),
                            onPressed: () async {
                              final confirm = await showDialog<bool>(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  title: const Text('Waive Penalty?'),
                                  content: const Text(
                                      'This will clear the student\'s pending penalty and restore their account.'),
                                  actions: [
                                    TextButton(
                                        onPressed: () =>
                                            Navigator.pop(ctx, false),
                                        child: const Text('Cancel')),
                                    TextButton(
                                        onPressed: () =>
                                            Navigator.pop(ctx, true),
                                        child: const Text('Waive',
                                            style: TextStyle(
                                                color: Colors.green))),
                                  ],
                                ),
                              );
                              if (confirm == true) _waive();
                            },
                          ),
                        )
                      else
                        const Text(
                          '✅ No pending penalty for this student.',
                          style: TextStyle(color: Colors.green),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value,
              style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}