// lib/core/models/outlet_model.dart

class Outlet {
  final int id;
  final String name;
  final String status;
  final int avgPrepTime;
  final String? photoUrl;
  final String? launchedAt;
  final String createdAt;

  Outlet({
    required this.id,
    required this.name,
    required this.status,
    required this.avgPrepTime,
    this.photoUrl,
    this.launchedAt,
    required this.createdAt,
  });

  factory Outlet.fromJson(Map<String, dynamic> json) => Outlet(
    id: json['id'],
    name: json['name'],
    status: json['status'],
    avgPrepTime: json['avgPrepTime'],
    photoUrl: json['photoUrl'],
    launchedAt: json['launchedAt'],
    createdAt: json['createdAt'],
  );
}