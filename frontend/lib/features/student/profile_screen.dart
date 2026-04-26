// lib/features/student/profile_screen.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/storage/secure_storage.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  String _name = '';
  String _email = '';
  String _accountStatus = '';
  String _noShowCount = '0';
  String _pendingPenalty = '0.0';
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _name = prefs.getString('name') ?? '';
      _email = prefs.getString('email') ?? '';
      _accountStatus = prefs.getString('accountStatus') ?? '';
      _noShowCount = prefs.getString('noShowCount') ?? '0';
      _pendingPenalty = prefs.getString('pendingPenalty') ?? '0.0';
      _loading = false;
    });
  }

  Future<void> _logout(BuildContext context) async {
    await StorageService.clearAll();
    if (context.mounted) context.go('/login');
  }

  Color _statusColor(String status) => switch (status) {
        'ACTIVE' => Colors.green,
        'WARNING' => Colors.orange,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    final penalty = double.tryParse(_pendingPenalty) ?? 0.0;
    final noShow = int.tryParse(_noShowCount) ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () => _logout(context),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Avatar
            Center(
              child: CircleAvatar(
                radius: 48,
                backgroundColor: Colors.deepOrange[100],
                child: Text(
                  _name.isNotEmpty ? _name[0].toUpperCase() : '?',
                  style: const TextStyle(
                      fontSize: 40,
                      fontWeight: FontWeight.bold,
                      color: Colors.deepOrange),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(
                _name,
                style: const TextStyle(
                    fontSize: 22, fontWeight: FontWeight.bold),
              ),
            ),
            Center(
              child: Text(
                _email,
                style: const TextStyle(color: Colors.grey),
              ),
            ),
            const SizedBox(height: 8),

            // Account status badge
            Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: _statusColor(_accountStatus).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  _accountStatus,
                  style: TextStyle(
                    color: _statusColor(_accountStatus),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 32),

            // Stats card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    const Text('Account Summary',
                        style: TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: _StatBox(
                            icon: Icons.block,
                            label: 'No-Shows',
                            value: '$noShow / 3',
                            color: noShow >= 2 ? Colors.red : Colors.orange,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _StatBox(
                            icon: Icons.currency_rupee,
                            label: 'Pending Penalty',
                            value: '₹${penalty.toStringAsFixed(2)}',
                            color: penalty > 0 ? Colors.red : Colors.green,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Quick links
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.receipt_long_outlined,
                        color: Colors.deepOrange),
                    title: const Text('My Orders'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/student/orders'),
                  ),
                  const Divider(height: 0),
                  ListTile(
                    leading: const Icon(Icons.notifications_outlined,
                        color: Colors.deepOrange),
                    title: const Text('Notifications'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/student/notifications'),
                  ),
                  if (penalty > 0) ...[
                    const Divider(height: 0),
                    ListTile(
                      leading: const Icon(Icons.warning_amber_rounded,
                          color: Colors.red),
                      title: const Text('Pay Penalty',
                          style: TextStyle(color: Colors.red)),
                      trailing: const Icon(Icons.chevron_right,
                          color: Colors.red),
                      onTap: () => context.go('/student/penalty'),
                    ),
                  ],
                ],
              ),
            ),

            const SizedBox(height: 32),

            // Logout button
            OutlinedButton.icon(
              onPressed: () => _logout(context),
              icon: const Icon(Icons.logout, color: Colors.red),
              label: const Text('Logout',
                  style: TextStyle(color: Colors.red)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.red),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatBox extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatBox({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 6),
          Text(value,
              style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: color)),
          Text(label,
              style: const TextStyle(color: Colors.grey, fontSize: 11),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }
}