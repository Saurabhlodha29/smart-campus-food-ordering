// lib/core/models/campus_model.dart

class Campus {
  final int id;
  final String name;
  final String location;
  final String emailDomain;
  final String status;
  final String createdAt;

  Campus({
    required this.id,
    required this.name,
    required this.location,
    required this.emailDomain,
    required this.status,
    required this.createdAt,
  });

  factory Campus.fromJson(Map<String, dynamic> json) => Campus(
        id: json['id'],
        name: json['name'],
        location: json['location'],
        emailDomain: json['emailDomain'],
        status: json['status'],
        createdAt: json['createdAt'],
      );
}