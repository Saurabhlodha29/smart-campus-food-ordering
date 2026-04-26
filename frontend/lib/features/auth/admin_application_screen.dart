import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';

class AdminApplicationScreen extends StatefulWidget {
  const AdminApplicationScreen({super.key});

  @override
  State<AdminApplicationScreen> createState() => _AdminApplicationScreenState();
}

class _AdminApplicationScreenState extends State<AdminApplicationScreen> {
  final _formKey = GlobalKey<FormState>();
  
  // These controllers capture the data the backend needs
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _designationController = TextEditingController();
  final _campusNameController = TextEditingController();
  final _domainController = TextEditingController();

  bool _isLoading = false;

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      // Endpoint: POST /api/admin-applications (Publicly accessible)
      await ApiClient.dio.post('/api/admin-applications', data: {
        'fullName': _nameController.text,
        'applicantEmail': _emailController.text,
        'designation': _designationController.text,
        'campusName': _campusNameController.text,
        'campusLocation': 'Main Campus', // Simple placeholder
        'campusEmailDomain': _domainController.text,
        'idCardPhotoUrl': 'https://via.placeholder.com/150', 
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Application Submitted!')));
        Navigator.pop(context); // Go back to Login
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Submission failed: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Application')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(controller: _nameController, decoration: const InputDecoration(labelText: 'Your Full Name'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _emailController, decoration: const InputDecoration(labelText: 'Work Email'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _designationController, decoration: const InputDecoration(labelText: 'Designation (e.g. Dean, Mess Lead)'), validator: (v) => v!.isEmpty ? 'Required' : null),
              const Divider(height: 40),
              TextFormField(controller: _campusNameController, decoration: const InputDecoration(labelText: 'College/Campus Name'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _domainController, decoration: const InputDecoration(labelText: 'Email Domain (e.g. @mit.edu)'), validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 30),
              _isLoading ? const CircularProgressIndicator() : ElevatedButton(onPressed: _submit, child: const Text('Submit Application')),
            ],
          ),
        ),
      ),
    );
  }
}