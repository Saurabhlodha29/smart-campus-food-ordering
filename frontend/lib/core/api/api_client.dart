// lib/core/api/api_client.dart

import 'package:dio/dio.dart';
import '../storage/secure_storage.dart';

class ApiClient {
  // Since you are testing on Chrome Web right now, localhost works perfectly!
  static const String baseUrl = 'http://localhost:8080';
  
  static late final Dio dio;

  static void init() {
    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ));

    // The Interceptor: Automatically adds the JWT token to every request
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await StorageService.getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // If the backend says the token is expired, clear the app storage
          await StorageService.clearAll();
          // We will trigger a redirect to the Login screen via GoRouter later
        }
        return handler.next(error);
      },
    ));
  }
}