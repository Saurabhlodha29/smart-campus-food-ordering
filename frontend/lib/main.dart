import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/api/api_client.dart';
import 'core/router/app_router.dart'; // Import our updated router
import 'core/theme/app_theme.dart'; // Import the new AppTheme

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  ApiClient.init();
  runApp(
    const ProviderScope(
      child: SmartCampusApp(),
    ),
  );
}

class SmartCampusApp extends StatelessWidget {
  const SmartCampusApp({super.key});

  @override
  Widget build(BuildContext context) {
    // We use .router to let GoRouter handle the navigation
    return MaterialApp.router(
      title: 'Smart Campus Food',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: appRouter,
    );
  }
}