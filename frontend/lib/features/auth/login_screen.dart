// lib/features/auth/login_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/storage/secure_storage.dart';
import 'auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields')),
      );
      return;
    }

    final success =
        await ref.read(authProvider.notifier).login(email, password);

    if (success && mounted) {
      // BUG FIX: previously hardcoded '/superadmin/dashboard' for every role.
      // Now we read the role that was saved to SharedPreferences during login
      // and route each user to their correct home screen.
      final role = await StorageService.getRole();

      if (!mounted) return;

      switch (role) {
        case 'SUPERADMIN':
          context.go('/superadmin/dashboard');
          break;
        case 'ADMIN':
          context.go('/admin/dashboard');
          break;
        case 'MANAGER':
          // Manager needs special handling: check outlet status first.
          // For now route to dashboard; outlet status check happens there.
          context.go('/manager/dashboard');
          break;
        case 'STUDENT':
          context.go('/student/home');
          break;
        default:
          // Unknown role — boot back to login cleanly
          await StorageService.clearAll();
          if (mounted) context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.fastfood, size: 80, color: Colors.deepOrange),
                const SizedBox(height: 24),
                const Text(
                  'Smart Campus Food',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 48),

                // Error message from auth provider
                if (authState.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16.0),
                    child: Text(
                      authState.error!,
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                  ),

                TextField(
                  controller: _emailController,
                  decoration: const InputDecoration(
                    labelText: 'Campus Email',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.email),
                  ),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock),
                  ),
                  obscureText: true,
                ),
                const SizedBox(height: 24),

                authState.isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : ElevatedButton(
                        onPressed: _handleLogin,
                        child: const Text('Login'),
                      ),

                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => context.push('/register'),
                  child: const Text('New student? Register here'),
                ),
                TextButton(
                  onPressed: () => context.push('/apply-admin'),
                  child: const Text('Apply to register your Campus'),
                ),
                TextButton(
                  onPressed: () => context.push('/apply-outlet'),
                  child: const Text('Apply to open a Food Outlet'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}