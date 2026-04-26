import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';

class StudentMainScaffold extends ConsumerWidget {
  final Widget child;
  const StudentMainScaffold({super.key, required this.child});

  int _calculateSelectedIndex(BuildContext context) {
    final String location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/student/home')) return 0;
    if (location.startsWith('/student/search')) return 1;
    if (location.startsWith('/student/orders')) return 2;
    if (location.startsWith('/student/profile')) return 3;
    return 0; // Default to home
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0:
        context.go('/student/home');
        break;
      case 1:
        // context.go('/student/search'); // Placeholder
        break;
      case 2:
        context.go('/student/orders');
        break;
      case 3:
        context.go('/student/profile');
        break;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedIndex = _calculateSelectedIndex(context);

    // Only show bottom bar on root tabs, hide on details, cart, etc.
    final String location = GoRouterState.of(context).matchedLocation;
    final bool showBottomNav = location == '/student/home' || 
                               location == '/student/search' || 
                               location == '/student/orders' || 
                               location == '/student/profile';

    return Scaffold(
      body: child,
      extendBody: true, // Needed to show body under the floating nav bar
      bottomNavigationBar: showBottomNav ? Container(
        margin: const EdgeInsets.only(left: 24, right: 24, bottom: 24),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(32),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 20,
              offset: const Offset(0, 10),
            )
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(32),
          child: BottomNavigationBar(
            currentIndex: selectedIndex,
            onTap: (index) => _onItemTapped(index, context),
            backgroundColor: Colors.white,
            selectedItemColor: AppTheme.primary,
            unselectedItemColor: Colors.grey.shade400,
            showSelectedLabels: false,
            showUnselectedLabels: false,
            type: BottomNavigationBarType.fixed,
            elevation: 0,
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.home_outlined),
                activeIcon: Icon(Icons.home),
                label: 'Home',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.search_outlined),
                activeIcon: Icon(Icons.search),
                label: 'Search',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.bookmark_outline),
                activeIcon: Icon(Icons.bookmark),
                label: 'Orders',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.person_outline),
                activeIcon: Icon(Icons.person),
                label: 'Profile',
              ),
            ],
          ),
        ),
      ) : null,
    );
  }
}
