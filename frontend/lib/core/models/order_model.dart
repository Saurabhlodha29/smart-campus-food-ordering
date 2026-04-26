// lib/core/models/order_model.dart

class Order {
  final int id;
  final String status;
  final double totalAmount;
  final String paymentMode;
  final String paymentStatus;
  final String readyAt;
  final String expiresAt;
  final String createdAt;

  Order({
    required this.id,
    required this.status,
    required this.totalAmount,
    required this.paymentMode,
    required this.paymentStatus,
    required this.readyAt,
    required this.expiresAt,
    required this.createdAt,
  });

  DateTime get readyAtDate => DateTime.parse(readyAt);
  DateTime get expiresAtDate => DateTime.parse(expiresAt);

  factory Order.fromJson(Map<String, dynamic> json) => Order(
    id: json['id'],
    status: json['status'],
    totalAmount: (json['totalAmount'] as num).toDouble(),
    paymentMode: json['paymentMode'],
    paymentStatus: json['paymentStatus'],
    readyAt: json['readyAt'],
    expiresAt: json['expiresAt'],
    createdAt: json['createdAt'],
  );
}