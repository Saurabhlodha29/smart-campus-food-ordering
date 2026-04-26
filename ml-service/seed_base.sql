-- 1. Create 2 more managers
INSERT INTO users (full_name, email, password_hash, role_id, account_status, is_active, pending_penalty_amount, no_show_count, created_at)
VALUES 
('Rajesh Manager', 'rajesh@canteen.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 3, 'ACTIVE', true, 0.0, 0, NOW()),
('Sita Manager', 'sita@canteen.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 3, 'ACTIVE', true, 0.0, 0, NOW())
ON CONFLICT (email) DO NOTHING;

-- 2. Create 2 more outlets (ACTIVE)
INSERT INTO outlets (name, manager_id, campus_id, status, avg_prep_time, created_at)
SELECT 'Quick Bites', id, 3, 'ACTIVE', 10, NOW() FROM users WHERE email = 'rajesh@canteen.com'
AND NOT EXISTS (SELECT 1 FROM outlets WHERE name = 'Quick Bites')
ON CONFLICT DO NOTHING;

INSERT INTO outlets (name, manager_id, campus_id, status, avg_prep_time, created_at)
SELECT 'Dhaba Corner', id, 4, 'ACTIVE', 15, NOW() FROM users WHERE email = 'sita@canteen.com'
AND NOT EXISTS (SELECT 1 FROM outlets WHERE name = 'Dhaba Corner')
ON CONFLICT DO NOTHING;

-- 3. Create 5 more students
INSERT INTO users (full_name, email, password_hash, role_id, account_status, is_active, pending_penalty_amount, no_show_count, campus_id, created_at)
VALUES 
('Arjun Sharma', 'arjun@student.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 4, 'ACTIVE', true, 0.0, 0, 3, NOW()),
('Priya Patel', 'priya@student.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 4, 'ACTIVE', true, 0.0, 0, 3, NOW()),
('Rahul Gupta', 'rahul@student.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 4, 'ACTIVE', true, 0.0, 0, 4, NOW()),
('Sneha Verma', 'sneha@student.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 4, 'ACTIVE', true, 0.0, 0, 4, NOW()),
('Ankit Singh', 'ankit@student.com', '$2a$10$8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX8.uX', 4, 'ACTIVE', true, 0.0, 0, 3, NOW())
ON CONFLICT (email) DO NOTHING;

-- 4. Add menu items for all outlets
-- Test Canteen (ID 1)
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT 1, 'Veg Burger', 70, 8, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM menu_items WHERE outlet_id = 1 AND name = 'Veg Burger');
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT 1, 'Chicken Burger', 90, 10, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM menu_items WHERE outlet_id = 1 AND name = 'Chicken Burger');
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT 1, 'French Fries', 50, 7, true, NOW() WHERE NOT EXISTS (SELECT 1 FROM menu_items WHERE outlet_id = 1 AND name = 'French Fries');

-- Quick Bites
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT id, 'Masala Dosa', 70, 10, true, NOW() FROM outlets WHERE name = 'Quick Bites' AND NOT EXISTS (SELECT 1 FROM menu_items WHERE name = 'Masala Dosa' AND outlet_id = (SELECT id FROM outlets WHERE name = 'Quick Bites'));
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT id, 'Idli Sambar', 45, 7, true, NOW() FROM outlets WHERE name = 'Quick Bites' AND NOT EXISTS (SELECT 1 FROM menu_items WHERE name = 'Idli Sambar' AND outlet_id = (SELECT id FROM outlets WHERE name = 'Quick Bites'));

-- Dhaba Corner
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT id, 'Chole Bhature', 60, 12, true, NOW() FROM outlets WHERE name = 'Dhaba Corner' AND NOT EXISTS (SELECT 1 FROM menu_items WHERE name = 'Chole Bhature' AND outlet_id = (SELECT id FROM outlets WHERE name = 'Dhaba Corner'));
INSERT INTO menu_items (outlet_id, name, price, prep_time, is_available, created_at)
SELECT id, 'Dal Makhani', 80, 15, true, NOW() FROM outlets WHERE name = 'Dhaba Corner' AND NOT EXISTS (SELECT 1 FROM menu_items WHERE name = 'Dal Makhani' AND outlet_id = (SELECT id FROM outlets WHERE name = 'Dhaba Corner'));
