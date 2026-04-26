// lib/features/manager/slot_management_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'manager_provider.dart';

class SlotManagementScreen extends ConsumerWidget {
  const SlotManagementScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final slotsAsync = ref.watch(managerSlotsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pickup Slots'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/manager/dashboard'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(managerSlotsProvider),
          ),
        ],
      ),
      body: slotsAsync.when(
        data: (slots) => slots.isEmpty
            ? const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.schedule, size: 64, color: Colors.grey),
                    SizedBox(height: 12),
                    Text('No slots created yet.',
                        style: TextStyle(color: Colors.grey)),
                    SizedBox(height: 4),
                    Text('Add slots so students can pick up orders.',
                        style: TextStyle(color: Colors.grey, fontSize: 13)),
                  ],
                ),
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: slots.length,
                itemBuilder: (context, index) {
                  final slot = slots[index];
                  final fillRatio = slot.maxOrders == 0
                      ? 0.0
                      : slot.currentOrders / slot.maxOrders;
                  final isFull = slot.isFull;

                  return Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.access_time,
                                  color: Colors.deepOrange),
                              const SizedBox(width: 8),
                              Text(
                                '${slot.startTime} – ${slot.endTime}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 15),
                              ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: isFull
                                      ? Colors.red[50]
                                      : Colors.green[50],
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  isFull ? 'Full' : 'Open',
                                  style: TextStyle(
                                    color: isFull ? Colors.red : Colors.green,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          LinearProgressIndicator(
                            value: fillRatio,
                            backgroundColor: Colors.grey[200],
                            color: isFull ? Colors.red : Colors.green,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${slot.currentOrders} / ${slot.maxOrders} orders',
                            style: const TextStyle(
                                color: Colors.grey, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateSlotDialog(context, ref),
        backgroundColor: Colors.deepOrange,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('Add Slot', style: TextStyle(color: Colors.white)),
      ),
    );
  }

  void _showCreateSlotDialog(BuildContext context, WidgetRef ref) {
    final startCtrl = TextEditingController();
    final endCtrl = TextEditingController();
    final maxCtrl = TextEditingController(text: '20');
    final formKey = GlobalKey<FormState>();

    Future<void> pickTime(
        BuildContext ctx, TextEditingController ctrl) async {
      final picked = await showTimePicker(
        context: ctx,
        initialTime: TimeOfDay.now(),
      );
      if (picked != null) {
        final h = picked.hour.toString().padLeft(2, '0');
        final m = picked.minute.toString().padLeft(2, '0');
        ctrl.text = '$h:$m';
      }
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
            left: 24, right: 24, top: 24,
          ),
          child: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Create Pickup Slot',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: startCtrl,
                        // NOT readOnly — allows typing AND picker tap
                        decoration: InputDecoration(
                          labelText: 'Start Time',
                          border: const OutlineInputBorder(),
                          hintText: 'HH:MM',
                          suffixIcon: IconButton(
                            icon: const Icon(Icons.access_time),
                            onPressed: () async {
                              await pickTime(ctx, startCtrl);
                              setModalState(() {});
                            },
                          ),
                        ),
                        validator: (v) => v!.isEmpty ? 'Required' : null,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: endCtrl,
                        decoration: InputDecoration(
                          labelText: 'End Time',
                          border: const OutlineInputBorder(),
                          hintText: 'HH:MM',
                          suffixIcon: IconButton(
                            icon: const Icon(Icons.access_time),
                            onPressed: () async {
                              await pickTime(ctx, endCtrl);
                              setModalState(() {});
                            },
                          ),
                        ),
                        validator: (v) => v!.isEmpty ? 'Required' : null,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: maxCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Max Orders',
                    border: OutlineInputBorder(),
                    helperText: 'How many orders can this slot handle?',
                  ),
                  keyboardType: TextInputType.number,
                  validator: (v) => v!.isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                 onPressed: () async {
                     if (!formKey.currentState!.validate()) return;
                     try {
                       final today = DateTime.now();
                       final pad = (int n) => n.toString().padLeft(2, '0');
                       final startDT = '${today.year}-${pad(today.month)}-${pad(today.day)}T${startCtrl.text}:00';
                       final endDT   = '${today.year}-${pad(today.month)}-${pad(today.day)}T${endCtrl.text}:00';
                       await ref.read(managerProvider.notifier).createSlot({
                         'startTime': startDT,
                         'endTime':   endDT,
                         'maxOrders': int.parse(maxCtrl.text),
                       });
                       if (ctx.mounted) Navigator.pop(ctx);
                     } catch (e) {
                       if (ctx.mounted) {
                         ScaffoldMessenger.of(ctx).showSnackBar(
                           SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
                         );
                       }
                     }
                },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepOrange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('Create Slot'),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}