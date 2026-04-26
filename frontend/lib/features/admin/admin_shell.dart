// lib/features/admin/admin_shell.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

const _orange = Color(0xFFFF5722);
const _subtitle = Color(0xFF64748B);

class AdminShell extends StatelessWidget {
  final Widget child;
  const AdminShell({super.key, required this.child});

  int _currentIndex(String location) {
    if (location.startsWith('/admin/outlet-apps')) return 1;
    if (location.startsWith('/admin/outlet-history')) return 1;
    if (location.startsWith('/admin/outlets')) return 2;
    if (location.startsWith('/admin/penalties')) return 3;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = _currentIndex(location);

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 20,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
            child: Row(
              children: [
                _NavItem(
                  icon: Icons.dashboard_rounded,
                  label: 'Dashboard',
                  selected: index == 0,
                  onTap: () => context.go('/admin/dashboard'),
                ),
                _NavItem(
                  icon: Icons.assignment_rounded,
                  label: 'Applications',
                  selected: index == 1,
                  onTap: () => context.go('/admin/outlet-apps'),
                ),
                _NavItem(
                  icon: Icons.storefront_rounded,
                  label: 'Outlets',
                  selected: index == 2,
                  onTap: () => context.go('/admin/outlets'),
                ),
                _NavItem(
                  icon: Icons.gavel_rounded,
                  label: 'Penalties',
                  selected: index == 3,
                  onTap: () => context.go('/admin/penalties'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color:
                selected ? _orange.withOpacity(0.08) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon,
                  color: selected ? _orange : _subtitle, size: 22),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: selected ? _orange : _subtitle,
                  fontSize: 10,
                  fontWeight:
                      selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
