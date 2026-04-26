// lib/features/student/student_shell.dart
// Persistent bottom nav bar for all student screens

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'student_provider.dart';

const _orange = Color(0xFFFF5722);
const _heading = Color(0xFF1E293B);
const _subtitle = Color(0xFF64748B);

class StudentShell extends ConsumerWidget {
  final Widget child;
  const StudentShell({super.key, required this.child});

  int _currentIndex(String location) {
    if (location.startsWith('/student/orders')) return 1;
    if (location.startsWith('/student/profile')) return 2;
    return 0;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = _currentIndex(location);
    final cart = ref.watch(cartProvider);
    final cartCount = cart.fold(0, (s, c) => s + c.quantity);

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
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(
              children: [
                _NavItem(
                  icon: Icons.home_rounded,
                  label: 'Home',
                  selected: index == 0,
                  onTap: () => context.go('/student/home'),
                ),
                _NavItem(
                  icon: Icons.receipt_long_rounded,
                  label: 'Orders',
                  selected: index == 1,
                  onTap: () => context.go('/student/orders'),
                ),
                _NavItem(
                  icon: Icons.person_rounded,
                  label: 'Profile',
                  selected: index == 2,
                  onTap: () => context.go('/student/profile'),
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
            color: selected ? _orange.withOpacity(0.08) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon,
                  color: selected ? _orange : _subtitle,
                  size: 22),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: selected ? _orange : _subtitle,
                  fontSize: 11,
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
