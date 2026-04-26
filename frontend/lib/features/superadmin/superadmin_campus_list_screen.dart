// lib/features/superadmin/superadmin_campus_list_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'superadmin_provider.dart';

class SuperAdminCampusListScreen extends ConsumerWidget {
  const SuperAdminCampusListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final campusesAsync = ref.watch(allCampusesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('All Campuses'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(allCampusesProvider),
          ),
        ],
      ),
      body: campusesAsync.when(
        data: (campuses) {
          if (campuses.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.account_balance_outlined,
                      size: 64, color: const Color(0xFF64748B)),
                  SizedBox(height: 12),
                  Text('No campuses registered.',
                      style: TextStyle(color: const Color(0xFF64748B))),
                ],
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(allCampusesProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: campuses.length,
              itemBuilder: (context, index) {
                final campus = campuses[index];
                final isActive = campus.status == 'ACTIVE';
                final statusColor = isActive ? const Color(0xFF10B981) : const Color(0xFFEF4444);
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: statusColor.withOpacity(0.15),
                      radius: 24,
                      child: Icon(Icons.account_balance,
                          color: statusColor, size: 22),
                    ),
                    title: Text(campus.name,
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(campus.location,
                            style: const TextStyle(fontSize: 12)),
                        Text('@${campus.emailDomain}',
                            style: const TextStyle(
                                fontSize: 11, color: const Color(0xFF64748B))),
                      ],
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: statusColor.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(campus.status,
                              style: TextStyle(
                                  color: statusColor,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600)),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.chevron_right),
                      ],
                    ),
                    onTap: () =>
                        context.push('/superadmin/campus/${campus.id}'),
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: const Color(0xFFEF4444)),
              const SizedBox(height: 12),
              Text('$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => ref.invalidate(allCampusesProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}