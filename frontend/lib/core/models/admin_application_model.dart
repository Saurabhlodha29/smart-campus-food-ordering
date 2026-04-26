class AdminApplication {
  final int id;
  final String fullName;
  final String applicantEmail;
  final String designation;
  final String idCardPhotoUrl;
  final String campusName;
  final String campusLocation;
  final String campusEmailDomain;
  final String status;          // PENDING | APPROVED | REJECTED
  final String? rejectionReason;
  final int attemptNumber;      // 1, 2, or 3
  final String createdAt;

  AdminApplication({
    required this.id,
    required this.fullName,
    required this.applicantEmail,
    required this.designation,
    required this.idCardPhotoUrl,
    required this.campusName,
    required this.campusLocation,
    required this.campusEmailDomain,
    required this.status,
    this.rejectionReason,
    required this.attemptNumber,
    required this.createdAt,
  });

  factory AdminApplication.fromJson(Map<String, dynamic> json) => AdminApplication(
    id: json['id'],
    fullName: json['fullName'],
    applicantEmail: json['applicantEmail'],
    designation: json['designation'],
    idCardPhotoUrl: json['idCardPhotoUrl'],
    campusName: json['campusName'],
    campusLocation: json['campusLocation'],
    campusEmailDomain: json['campusEmailDomain'],
    status: json['status'],
    rejectionReason: json['rejectionReason'],
    attemptNumber: json['attemptNumber'],
    createdAt: json['createdAt'],
  );
}