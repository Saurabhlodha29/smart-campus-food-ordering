class MenuItem {
  final int id;
  final String name;
  final double price;
  final int prepTime;
  final String? photoUrl;
  final bool isAvailable;
  final String createdAt;
  final int? outletId;

  MenuItem({
    required this.id,
    required this.name,
    required this.price,
    required this.prepTime,
    this.photoUrl,
    required this.isAvailable,
    required this.createdAt,
    this.outletId,
  });

  factory MenuItem.fromJson(Map<String, dynamic> json) => MenuItem(
    id: json['id'],
    name: json['name'],
    price: (json['price'] as num).toDouble(),
    prepTime: json['prepTime'],
    photoUrl: json['photoUrl'],
    isAvailable: json['isAvailable'] ?? true,
    createdAt: json['createdAt'],
    outletId: json['outletId'],
  );
}