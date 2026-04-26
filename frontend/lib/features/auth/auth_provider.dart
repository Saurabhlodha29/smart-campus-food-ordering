// lib/features/auth/auth_provider.dart

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/models/auth_response_model.dart';
import '../../core/storage/secure_storage.dart';

class AuthState {
  final bool isLoading;
  final String? error;

  AuthState({this.isLoading = false, this.error});
}

// 1. Changed StateNotifier to Notifier (Modern Riverpod 2.0+ Syntax)
class AuthNotifier extends Notifier<AuthState> {
  
  // 2. Notifier requires a build() method to set the initial state
  @override
  AuthState build() {
    return AuthState(); 
  }

  Future<bool> login(String email, String password) async {
    state = AuthState(isLoading: true);
    try {
      final response = await ApiClient.dio.post(
        '/api/auth/login',
        data: {
          'email': email,
          'password': password,
        },
      );

      final authData = AuthResponse.fromJson(response.data);

      await StorageService.saveToken(authData.token);
      await StorageService.saveUserData(authData);

      state = AuthState(isLoading: false);
      return true; 
    } on DioException catch (e) {
      state = AuthState(
        isLoading: false,
        error: e.response?.data['message'] ?? 'Invalid email or password.',
      );
      return false; 
    } catch (e) {
      state = AuthState(isLoading: false, error: 'Network error occurred.');
      return false; 
    }
  }
}

// 3. Changed StateNotifierProvider to NotifierProvider
final authProvider = NotifierProvider<AuthNotifier, AuthState>(() {
  return AuthNotifier();
});