class PickupSlot {
  final int id;
  final int outletId;
  final String startTime;
  final String endTime;
  final int maxOrders;
  final int currentOrders;

  PickupSlot({
    required this.id,
    required this.outletId,
    required this.startTime,
    required this.endTime,
    required this.maxOrders,
    required this.currentOrders,
  });

  static String _formatTime(String dt) {
    final t = DateTime.parse(dt);
    final h = t.hour > 12 ? t.hour - 12 : (t.hour == 0 ? 12 : t.hour);
    final m = t.minute.toString().padLeft(2, '0');
    final period = t.hour >= 12 ? 'PM' : 'AM';
    return '$h:$m $period';
  }

  bool get isFull => currentOrders >= maxOrders;

  factory PickupSlot.fromJson(Map<String, dynamic> json) => PickupSlot(
    id: json['id'],
    outletId: json['outletId'] ?? 0,
    startTime: _formatTime(json['startTime']),
    endTime: _formatTime(json['endTime']),
    maxOrders: json['maxOrders'],
    currentOrders: json['currentOrders'] ?? 0,
  );
}