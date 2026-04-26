// lib/core/storage/secure_storage.dart

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/auth_response_model.dart';

class StorageService {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'jwt_token';

  // --- TOKEN OPERATIONS ---

  static Future<void> saveToken(String token) async {
    await _storage.write(key: _tokenKey, value: token);
  }

  static Future<String?> getToken() async {
    return await _storage.read(key: _tokenKey);
  }

  static Future<void> deleteToken() async {
    await _storage.delete(key: _tokenKey);
  }

  // --- USER DATA OPERATIONS (SharedPreferences) ---

  static Future<void> saveUserData(AuthResponse data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('role', data.role);
    await prefs.setString('name', data.name);
    await prefs.setString('email', data.email);
    await prefs.setString('userId', data.id);
    await prefs.setString('accountStatus', data.accountStatus);
    await prefs.setString('pendingPenalty', data.pendingPenalty);
    await prefs.setString('noShowCount', data.noShowCount);
    // Save campusId if backend returns it (students need it to fetch outlets)
    if (data.campusId != null) {
      await prefs.setString('campusId', data.campusId!);
    }
  }

  static Future<String?> getCampusId() async =>
      (await SharedPreferences.getInstance()).getString('campusId');

  // Convenience getters so screens don't need to touch SharedPreferences directly
  static Future<String?> getRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('role');
  }

  static Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('userId');
  }

  static Future<String?> getName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('name');
  }

  static Future<String?> getEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('email');
  }

  static Future<String?> getAccountStatus() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('accountStatus');
  }

  static Future<String?> getPendingPenalty() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('pendingPenalty');
  }

  // --- THE MASTER WIPE ---
  // BUG FIX: previously only removed 'role', leaving name/email/userId/accountStatus
  // behind — causing the "ghost SuperAdmin view" when a different role logged in.
  // Now we nuke the JWT AND call prefs.clear() to wipe every key at once.

  static Future<void> clearAll() async {
    // 1. Delete the secure JWT token
    await _storage.delete(key: _tokenKey);

    // 2. Wipe ALL SharedPreferences keys in one call
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
}