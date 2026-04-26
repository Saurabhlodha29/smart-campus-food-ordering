// lib/features/manager/manager_shell.dart
// Persistent bottom nav bar for Manager screens

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

const _orange = Color(0xFFFF5722);
const _subtitle = Color(0xFF64748B);

class ManagerShell extends StatelessWidget {
  final Widget child;
  const ManagerShell({super.key, required this.child});

  int _currentIndex(String location) {
    if (location.startsWith('/manager/menu')) return 1;
    if (location.startsWith('/manager/slots')) return 2;
    if (location.startsWith('/manager/ledger')) return 3;
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
                  label: 'Orders',
                  selected: index == 0,
                  onTap: () => context.go('/manager/dashboard'),
                ),
                _NavItem(
                  icon: Icons.restaurant_menu_rounded,
                  label: 'Menu',
                  selected: index == 1,
                  onTap: () => context.go('/manager/menu'),
                ),
                _NavItem(
                  icon: Icons.schedule_rounded,
                  label: 'Slots',
                  selected: index == 2,
                  onTap: () => context.go('/manager/slots'),
                ),
                _NavItem(
                  icon: Icons.account_balance_wallet_rounded,
                  label: 'Ledger',
                  selected: index == 3,
                  onTap: () => context.go('/manager/ledger'),
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
