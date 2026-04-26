// lib/core/models/outlet_application_model.dart

class OutletApplication {
  final int id;
  final String managerName;
  final String managerEmail;
  final String outletName;
  final String? outletDescription;
  final int avgPrepTime;
  final String licenseDocUrl;
  final String? outletPhotoUrl;
  final String status; // PENDING | APPROVED | REJECTED
  final String? rejectionReason;
  final int attemptNumber;
  final String createdAt;

  OutletApplication({
    required this.id,
    required this.managerName,
    required this.managerEmail,
    required this.outletName,
    this.outletDescription,
    required this.avgPrepTime,
    required this.licenseDocUrl,
    this.outletPhotoUrl,
    required this.status,
    this.rejectionReason,
    required this.attemptNumber,
    required this.createdAt,
  });

  factory OutletApplication.fromJson(Map<String, dynamic> json) =>
      OutletApplication(
        id: json['id'],
        managerName: json['managerName'],
        managerEmail: json['managerEmail'],
        outletName: json['outletName'],
        outletDescription: json['outletDescription'],
        avgPrepTime: json['avgPrepTime'],
        licenseDocUrl: json['licenseDocUrl'],
        outletPhotoUrl: json['outletPhotoUrl'],
        status: json['status'],
        rejectionReason: json['rejectionReason'],
        attemptNumber: json['attemptNumber'],
        createdAt: json['createdAt'],
      );
}