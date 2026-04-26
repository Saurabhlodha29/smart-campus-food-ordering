// lib/features/student/student_home_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/models/outlet_model.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/app_theme.dart';
import 'student_provider.dart';

class StudentHomeScreen extends ConsumerStatefulWidget {
  const StudentHomeScreen({super.key});

  @override
  ConsumerState<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends ConsumerState<StudentHomeScreen> {
  String _studentName = '';
  String _pendingPenalty = '0.0';
  String _accountStatus = '';

  @override
  void initState() {
    super.initState();
    _loadUserData();
  }

  Future<void> _loadUserData() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _studentName = prefs.getString('name') ?? '';
      _pendingPenalty = prefs.getString('pendingPenalty') ?? '0.0';
      _accountStatus = prefs.getString('accountStatus') ?? '';
    });
  }

  Future<void> _logout(BuildContext context) async {
    await StorageService.clearAll();
    if (context.mounted) context.go('/login');
  }

  Color _outletStatusColor(String status) => switch (status) {
        'ACTIVE' => Colors.green,
        'SUSPENDED' => Colors.red,
        'PENDING_LAUNCH' => Colors.amber,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    final outletsAsync = ref.watch(studentOutletsProvider);
    final penalty = double.tryParse(_pendingPenalty) ?? 0.0;
    final hasWarning = _accountStatus == 'WARNING' || penalty > 0;

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(studentOutletsProvider),
        child: CustomScrollView(
          slivers: [
            // Top Section & Greeting
            SliverToBoxAdapter(
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 24, 16, 16),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 24,
                        backgroundColor: AppTheme.surface,
                        child: Text(
                          _studentName.isNotEmpty ? _studentName[0].toUpperCase() : '?',
                          style: const TextStyle(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.bold,
                              fontSize: 18),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Good Morning,',
                              style: TextStyle(
                                  fontSize: 14, color: AppTheme.textSecondary),
                            ),
                            Text(
                              _studentName,
                              style: const TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.text),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.notifications_outlined,
                            size: 28, color: AppTheme.text),
                        onPressed: () => context.push('/student/notifications'),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // Penalty warning banner
            if (hasWarning)
              SliverToBoxAdapter(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red[50],
                    border: Border.all(color: Colors.red.shade200),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded, color: Colors.red),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'You have an outstanding penalty of ₹$_pendingPenalty.',
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.push('/student/penalty'),
                        child: const Text('Pay Now',
                            style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
              ),

            // Search Bar
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'What are you craving?',
                    hintStyle: TextStyle(color: Colors.grey.shade400),
                    prefixIcon: const Icon(Icons.search, color: Colors.grey),
                    suffixIcon: Container(
                      margin: const EdgeInsets.all(8),
                      decoration: const BoxDecoration(
                        color: AppTheme.primary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.tune, color: Colors.white, size: 20),
                    ),
                    filled: true,
                    fillColor: AppTheme.surface,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(30),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 0),
                  ),
                ),
              ),
            ),

            // Quick Actions (Chips)
            SliverToBoxAdapter(
              child: SizedBox(
                height: 100,
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  scrollDirection: Axis.horizontal,
                  children: [
                    _QuickActionChip(icon: Icons.local_dining, label: 'All'),
                    _QuickActionChip(icon: Icons.fastfood, label: 'Fast Food'),
                    _QuickActionChip(icon: Icons.local_cafe, label: 'Beverages'),
                    _QuickActionChip(icon: Icons.set_meal, label: 'Healthy'),
                    _QuickActionChip(icon: Icons.icecream, label: 'Desserts'),
                  ],
                ),
              ),
            ),

            // Promotional Slider
            SliverToBoxAdapter(
              child: SizedBox(
                height: 160,
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  scrollDirection: Axis.horizontal,
                  children: [
                    _PromoCard(
                      title: 'Campus Specials',
                      subtitle: 'Up to 20% off',
                      imageUrl: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80',
                    ),
                    _PromoCard(
                      title: 'Visa Dining Collection',
                      subtitle: 'Exclusive perks',
                      imageUrl: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80',
                    ),
                  ],
                ),
              ),
            ),

            // Section label
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.fromLTRB(16, 24, 16, 12),
                child: Text('Restaurants Nearby',
                    style: TextStyle(
                        fontSize: 18,
                        color: AppTheme.text,
                        fontWeight: FontWeight.bold)),
              ),
            ),

            // Outlet list
            outletsAsync.when(
              data: (outlets) {
                if (outlets.isEmpty) {
                  return const SliverFillRemaining(
                     hasScrollBody: false,
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.storefront_outlined,
                              size: 64, color: Colors.grey),
                          SizedBox(height: 12),
                          Text('No outlets available yet.',
                              style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    ),
                  );
                }
                return SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 100), // extra padding for bottom nav
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) {
                        final outlet = outlets[index];
                        final isActive = outlet.status == 'ACTIVE';
                        return _OutletCard(
                          outlet: outlet,
                          statusColor: _outletStatusColor(outlet.status),
                          onTap: isActive && !hasWarning
                              ? () => context.push(
                                  '/student/outlet/${outlet.id}')
                              : null,
                        );
                      },
                      childCount: outlets.length,
                    ),
                  ),
                );
              },
              loading: () => const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
              error: (err, _) => SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline,
                            size: 48, color: Colors.red),
                        const SizedBox(height: 12),
                        Text('$err', textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: () =>
                              ref.invalidate(studentOutletsProvider),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
      // Cart FAB — only show if cart has items
      floatingActionButton: Consumer(
        builder: (context, ref, _) {
          final cart = ref.watch(cartProvider);
          if (cart.isEmpty) return const SizedBox.shrink();
          return FloatingActionButton.extended(
            onPressed: () => context.push('/student/cart'),
            backgroundColor: AppTheme.primary,
            elevation: 8,
            icon: const Icon(Icons.shopping_cart, color: Colors.white),
            label: Text(
              '${cart.fold(0, (s, c) => s + c.quantity)} items · ₹${ref.read(cartProvider.notifier).total.toStringAsFixed(2)}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
          );
        },
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}

class _OutletCard extends StatelessWidget {
  final Outlet outlet;
  final Color statusColor;
  final VoidCallback? onTap;

  const _OutletCard({
    required this.outlet,
    required this.statusColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDisabled = onTap == null;
    return Opacity(
      opacity: isDisabled ? 0.5 : 1.0,
      child: Container(
        margin: const EdgeInsets.only(bottom: 20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24.0),
          boxShadow: AppTheme.softShadows,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24.0),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTap,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Outlet photo
                  Container(
                    height: 160,
                    color: AppTheme.surface,
                    child: outlet.photoUrl != null
                        ? Image.network(
                            outlet.photoUrl!,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const Center(
                                child: Icon(Icons.storefront,
                                    size: 48, color: Colors.grey)),
                          )
                        : Image.network(
                            'https://images.unsplash.com/photo-1552566626-52f8b828add9?w=600&q=80',
                            width: double.infinity,
                            fit: BoxFit.cover,
                          ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                outlet.name,
                                style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.text),
                              ),
                              const SizedBox(height: 6),
                              Row(
                                children: [
                                  const Icon(Icons.timer_outlined,
                                      size: 16, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Text(
                                    '~${outlet.avgPrepTime} min prep time',
                                    style: const TextStyle(
                                        color: Colors.grey, fontSize: 13),
                                  ),
                                  const SizedBox(width: 12),
                                  const Icon(Icons.star,
                                      size: 16, color: Colors.amber),
                                  const SizedBox(width: 4),
                                  const Text(
                                    '4.8', // placeholder for rating
                                    style: TextStyle(
                                        color: Colors.grey, fontSize: 13),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        // Status badge / Action
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: statusColor.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            outlet.status == 'ACTIVE' ? 'Order' : outlet.status,
                            style: TextStyle(
                                color: statusColor,
                                fontSize: 12,
                                fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActionChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _QuickActionChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 16.0),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.background,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Icon(icon, color: AppTheme.primary, size: 28),
          ),
          const SizedBox(height: 8),
          Text(label,
              style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 12)),
        ],
      ),
    );
  }
}

class _PromoCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final String imageUrl;

  const _PromoCard(
      {required this.title, required this.subtitle, required this.imageUrl});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      margin: const EdgeInsets.only(right: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        image: DecorationImage(
          image: NetworkImage(imageUrl),
          fit: BoxFit.cover,
          colorFilter:
              ColorFilter.mode(Colors.black.withOpacity(0.3), BlendMode.darken),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Text(
              subtitle,
              style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 12,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }
}