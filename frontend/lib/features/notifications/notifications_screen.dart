// lib/features/notifications/notifications_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';

// ---------------------------------------------------------------------------
// MODEL
// ---------------------------------------------------------------------------

class AppNotification {
  final int id;
  final String title;
  final String message;
  final String type;
  final bool isRead;
  final String createdAt;

  AppNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.type,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) =>
      AppNotification(
        id: json['id'],
        title: json['title'] ?? '',
        message: json['message'] ?? '',
        type: json['type'] ?? '',
        isRead: json['isRead'] ?? false,
        createdAt: json['createdAt'] ?? '',
      );
}

// ---------------------------------------------------------------------------
// PROVIDERS
// ---------------------------------------------------------------------------

final notificationsProvider =
    FutureProvider<List<AppNotification>>((ref) async {
  final response = await ApiClient.dio.get('/api/notifications');
  return (response.data as List)
      .map((n) => AppNotification.fromJson(n))
      .toList();
});

final unreadCountProvider = FutureProvider<int>((ref) async {
  final response =
      await ApiClient.dio.get('/api/notifications/unread-count');
  return response.data['count'] ?? 0;
});

class NotificationsNotifier extends Notifier<void> {
  @override
  void build() {}

  Future<void> markAllRead() async {
    await ApiClient.dio.patch('/api/notifications/read-all');
    ref.invalidate(notificationsProvider);
    ref.invalidate(unreadCountProvider);
  }

  Future<void> markOneRead(int id) async {
    await ApiClient.dio.patch('/api/notifications/$id/read');
    ref.invalidate(notificationsProvider);
    ref.invalidate(unreadCountProvider);
  }
}

final notificationsNotifierProvider =
    NotifierProvider<NotificationsNotifier, void>(
        () => NotificationsNotifier());

// ---------------------------------------------------------------------------
// SCREEN
// ---------------------------------------------------------------------------

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  IconData _typeIcon(String type) => switch (type) {
        'ORDER_PLACED' => Icons.receipt_long,
        'ORDER_READY' => Icons.check_circle,
        'ORDER_EXPIRED' => Icons.timer_off,
        'PENALTY' => Icons.warning_amber,
        'OUTLET_APPROVED' => Icons.storefront,
        'OUTLET_REJECTED' => Icons.cancel,
        'ADMIN_APPROVED' => Icons.verified_user,
        _ => Icons.notifications,
      };

  Color _typeColor(String type) => switch (type) {
        'ORDER_PLACED' => Colors.blue,
        'ORDER_READY' => Colors.green,
        'ORDER_EXPIRED' => Colors.red,
        'PENALTY' => Colors.orange,
        'OUTLET_APPROVED' => Colors.green,
        'OUTLET_REJECTED' => Colors.red,
        'ADMIN_APPROVED' => Colors.green,
        _ => Colors.grey,
      };

  String _formatTime(String createdAt) {
    try {
      final dt = DateTime.parse(createdAt);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      return '${diff.inDays}d ago';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifAsync = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: () async {
              await ref
                  .read(notificationsNotifierProvider.notifier)
                  .markAllRead();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('All marked as read')),
                );
              }
            },
            child: const Text('Mark all read'),
          ),
        ],
      ),
      body: notifAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_none, size: 80, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No notifications yet',
                      style: TextStyle(fontSize: 18, color: Colors.grey)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(notificationsProvider),
            child: ListView.builder(
              itemCount: notifications.length,
              itemBuilder: (context, index) {
                final n = notifications[index];
                final color = _typeColor(n.type);

                return InkWell(
                  onTap: () async {
                    if (!n.isRead) {
                      await ref
                          .read(notificationsNotifierProvider.notifier)
                          .markOneRead(n.id);
                    }
                  },
                  child: Container(
                    decoration: BoxDecoration(
                      color: n.isRead ? null : color.withOpacity(0.05),
                      border: Border(
                        bottom: BorderSide(color: Colors.grey[200]!),
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 14),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Icon
                        Container(
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            color: color.withOpacity(0.15),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(_typeIcon(n.type),
                              color: color, size: 20),
                        ),
                        const SizedBox(width: 12),

                        // Content
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      n.title,
                                      style: TextStyle(
                                        fontWeight: n.isRead
                                            ? FontWeight.normal
                                            : FontWeight.bold,
                                        fontSize: 14,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    _formatTime(n.createdAt),
                                    style: const TextStyle(
                                        color: Colors.grey, fontSize: 11),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                n.message,
                                style: const TextStyle(
                                    color: Colors.grey, fontSize: 13),
                              ),
                            ],
                          ),
                        ),

                        // Unread dot
                        if (!n.isRead)
                          Padding(
                            padding: const EdgeInsets.only(left: 8, top: 4),
                            child: Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: color,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ),
                      ],
                    ),
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
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 12),
              Text('$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => ref.invalidate(notificationsProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}