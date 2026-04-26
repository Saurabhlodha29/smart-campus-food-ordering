// lib/core/models/auth_response_model.dart

class AuthResponse {
  final String token;
  final String role;
  final String name;
  final String email;
  final String id;
  final String accountStatus;
  final String pendingPenalty;
  final String noShowCount;
  final String? campusId; // null for SUPERADMIN (no campus)

  AuthResponse({
    required this.token,
    required this.role,
    required this.name,
    required this.email,
    required this.id,
    required this.accountStatus,
    required this.pendingPenalty,
    required this.noShowCount,
    this.campusId,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) => AuthResponse(
        token: json['token'] ?? '',
        role: json['role'] ?? '',
        name: json['name'] ?? '',
        email: json['email'] ?? '',
        id: json['id']?.toString() ?? '',
        accountStatus: json['accountStatus'] ?? '',
        pendingPenalty: json['pendingPenalty']?.toString() ?? '0.0',
        noShowCount: json['noShowCount']?.toString() ?? '0',
        campusId: json['campusId']?.toString(),
      );
}