// lib/features/auth/outlet_application_screen.dart

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';

class OutletApplicationScreen extends StatefulWidget {
  const OutletApplicationScreen({super.key});

  @override
  State<OutletApplicationScreen> createState() =>
      _OutletApplicationScreenState();
}

class _OutletApplicationScreenState extends State<OutletApplicationScreen> {
  final _formKey = GlobalKey<FormState>();

  final _managerNameCtrl = TextEditingController();
  final _managerEmailCtrl = TextEditingController();
  final _outletNameCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  final _prepTimeCtrl = TextEditingController();
  final _licenseUrlCtrl = TextEditingController();

  bool _isLoading = false;
  bool _loadingCampuses = true;

  List<Map<String, dynamic>> _campuses = [];
  int? _selectedCampusId;

  @override
  void initState() {
    super.initState();
    _loadCampuses();
  }

  Future<void> _loadCampuses() async {
    try {
      final plainDio = Dio(BaseOptions(
        baseUrl: ApiClient.dio.options.baseUrl,
        connectTimeout: ApiClient.dio.options.connectTimeout,
        receiveTimeout: ApiClient.dio.options.receiveTimeout,
      ));
      final response = await plainDio.get('/api/campuses');
      setState(() {
        _campuses = List<Map<String, dynamic>>.from(response.data);
        _loadingCampuses = false;
      });
    } catch (e) {
      setState(() => _loadingCampuses = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not load campuses: $e')),
        );
      }
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedCampusId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a campus')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ApiClient.dio.post('/api/outlet-applications', data: {
        'managerName': _managerNameCtrl.text.trim(),
        'managerEmail': _managerEmailCtrl.text.trim(),
        'outletName': _outletNameCtrl.text.trim(),
        'outletDescription': _descriptionCtrl.text.trim(),
        'avgPrepTime': int.parse(_prepTimeCtrl.text.trim()),
        'licenseDocUrl': _licenseUrlCtrl.text.trim().isEmpty
            ? 'https://via.placeholder.com/150'
            : _licenseUrlCtrl.text.trim(),
        'campusId': _selectedCampusId,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Application submitted! Wait for campus admin approval.'),
            backgroundColor: Colors.green,
          ),
        );
        context.go('/login');
      }
    } on DioException catch (e) {
      final msg = e.response?.data['message'] ?? 'Submission failed.';
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Network error. Is the backend running?'),
              backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _managerNameCtrl.dispose();
    _managerEmailCtrl.dispose();
    _outletNameCtrl.dispose();
    _descriptionCtrl.dispose();
    _prepTimeCtrl.dispose();
    _licenseUrlCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Apply to Open a Food Outlet'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/login'),
        ),
      ),
      body: _loadingCampuses
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Header
                      const Icon(Icons.storefront,
                          size: 64, color: Colors.deepOrange),
                      const SizedBox(height: 12),
                      const Text(
                        'Outlet Application',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 22, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Your application will be reviewed by the campus admin.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 32),

                      // ── YOUR DETAILS ─────────────────────────────────────
                      const _SectionHeader(title: 'Your Details'),
                      const SizedBox(height: 12),

                      TextFormField(
                        controller: _managerNameCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Your Full Name',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                        textCapitalization: TextCapitalization.words,
                        validator: (v) =>
                            v!.trim().isEmpty ? 'Required' : null,
                      ),
                      const SizedBox(height: 16),

                      TextFormField(
                        controller: _managerEmailCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Your Email',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.email_outlined),
                          helperText:
                              'This will be your login email if approved',
                        ),
                        keyboardType: TextInputType.emailAddress,
                        autocorrect: false,
                        validator: (v) {
                          if (v!.trim().isEmpty) return 'Required';
                          if (!v.contains('@')) return 'Enter a valid email';
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),

                      // ── OUTLET DETAILS ───────────────────────────────────
                      const _SectionHeader(title: 'Outlet Details'),
                      const SizedBox(height: 12),

                      TextFormField(
                        controller: _outletNameCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Outlet Name',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.storefront_outlined),
                        ),
                        textCapitalization: TextCapitalization.words,
                        validator: (v) =>
                            v!.trim().isEmpty ? 'Required' : null,
                      ),
                      const SizedBox(height: 16),

                      TextFormField(
                        controller: _descriptionCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Outlet Description (optional)',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.description_outlined),
                          hintText: 'e.g. North Indian food, snacks, beverages',
                        ),
                        maxLines: 2,
                      ),
                      const SizedBox(height: 16),

                      TextFormField(
                        controller: _prepTimeCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Average Prep Time (minutes)',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.timer_outlined),
                          hintText: 'e.g. 15',
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) {
                          if (v!.trim().isEmpty) return 'Required';
                          if (int.tryParse(v) == null) return 'Enter a number';
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),

                      // ── CAMPUS SELECTION ─────────────────────────────────
                      const _SectionHeader(title: 'Campus'),
                      const SizedBox(height: 12),

                      DropdownButtonFormField<int>(
                        value: _selectedCampusId,
                        decoration: const InputDecoration(
                          labelText: 'Select Campus',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.account_balance_outlined),
                        ),
                        items: _campuses
                            .map((c) => DropdownMenuItem<int>(
                                  value: c['id'] as int,
                                  child: Text(c['name'] ?? 'Unknown'),
                                ))
                            .toList(),
                        onChanged: (val) =>
                            setState(() => _selectedCampusId = val),
                        validator: (v) =>
                            v == null ? 'Please select a campus' : null,
                      ),
                      const SizedBox(height: 24),

                      // ── DOCUMENTS ────────────────────────────────────────
                      const _SectionHeader(title: 'License / Permission Document'),
                      const SizedBox(height: 8),

                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blue[50],
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.blue[200]!),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.info_outline,
                                color: Colors.blue, size: 18),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Upload is not available yet. Paste a link to your document below, or leave blank to use a placeholder.',
                                style:
                                    TextStyle(color: Colors.blue, fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),

                      TextFormField(
                        controller: _licenseUrlCtrl,
                        decoration: const InputDecoration(
                          labelText: 'License Document URL (optional)',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.link),
                          hintText: 'https://drive.google.com/...',
                        ),
                        keyboardType: TextInputType.url,
                        autocorrect: false,
                      ),
                      const SizedBox(height: 32),

                      // Submit button
                      _isLoading
                          ? const Center(child: CircularProgressIndicator())
                          : ElevatedButton(
                              onPressed: _submit,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.deepOrange,
                                foregroundColor: Colors.white,
                                padding:
                                    const EdgeInsets.symmetric(vertical: 16),
                              ),
                              child: const Text(
                                'Submit Application',
                                style: TextStyle(
                                    fontSize: 16, fontWeight: FontWeight.bold),
                              ),
                            ),

                      const SizedBox(height: 12),
                      TextButton(
                        onPressed: () => context.go('/login'),
                        child: const Text('Back to Login'),
                      ),
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(title,
            style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: Colors.deepOrange)),
        const SizedBox(width: 8),
        const Expanded(child: Divider()),
      ],
    );
  }
}