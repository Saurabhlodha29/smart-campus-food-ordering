# Database Schema — Smart Campus Food Ordering System

This document defines the initial **logical database schema** for the Smart Campus Food Ordering System.
The schema is designed to support **multi-campus operation**, **role-based access**, and **secure onboarding**.

This schema is considered **FROZEN for Phase 1**. Any change must be justified and reviewed.

---

## 1. roles

Defines system roles. Roles are stored in the database (not hardcoded).

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| name | VARCHAR(50) | UNIQUE, NOT NULL |

### Predefined Roles
- SUPER_ADMIN  
- CAMPUS_ADMIN  
- CAFE_MANAGER  
- STUDENT  

---

## 2. campuses

Represents a college or university.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| name | VARCHAR(150) | NOT NULL |
| location | VARCHAR(150) | NOT NULL |
| email_domain | VARCHAR(100) | NOT NULL |
| status | VARCHAR(20) | NOT NULL (`PENDING`, `ACTIVE`, `SUSPENDED`) |
| created_at | TIMESTAMP | DEFAULT current timestamp |

### Rules
- Campus remains unusable unless status = `ACTIVE`
- Campus is created via self-registration and approved by Super Admin

---

## 3. users

Stores all system users (single table for all roles).

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| full_name | VARCHAR(120) | NOT NULL |
| email | VARCHAR(150) | UNIQUE, NOT NULL |
| password_hash | TEXT | NOT NULL |
| role_id | BIGINT | Foreign Key → roles(id) |
| campus_id | BIGINT | Foreign Key → campuses(id), NULL allowed |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMP | DEFAULT current timestamp |

### Rules
- SUPER_ADMIN → campus_id must be NULL
- All other roles → campus_id must NOT be NULL

---

## 4. outlets

Represents a food outlet or cafe within a campus.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| campus_id | BIGINT | Foreign Key → campuses(id) |
| manager_id | BIGINT | Foreign Key → users(id) |
| name | VARCHAR(120) | NOT NULL |
| status | VARCHAR(20) | NOT NULL (`PENDING`, `ACTIVE`, `SUSPENDED`) |
| avg_prep_time | INTEGER | Average preparation time in minutes |
| created_at | TIMESTAMP | DEFAULT current timestamp |

### Rules
- Outlet registration requires Campus Admin approval
- Only ACTIVE outlets are visible to students

---

## 5. menu_items

Defines menu items offered by an outlet.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| outlet_id | BIGINT | Foreign Key → outlets(id) |
| name | VARCHAR(120) | NOT NULL |
| price | DECIMAL(8,2) | NOT NULL |
| prep_time | INTEGER | Preparation time in minutes |
| is_available | BOOLEAN | DEFAULT true |

---

## 6. pickup_slots

Controls pickup time slots to reduce crowding.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| outlet_id | BIGINT | Foreign Key → outlets(id) |
| start_time | TIMESTAMP | NOT NULL |
| end_time | TIMESTAMP | NOT NULL |
| capacity | INTEGER | NOT NULL |

---

## 7. orders

Represents a customer order.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| student_id | BIGINT | Foreign Key → users(id) |
| outlet_id | BIGINT | Foreign Key → outlets(id) |
| pickup_slot_id | BIGINT | Foreign Key → pickup_slots(id) |
| status | VARCHAR(20) | NOT NULL |
| total_amount | DECIMAL(10,2) | NOT NULL |
| created_at | TIMESTAMP | DEFAULT current timestamp |

### Order Status Flow (STRICT)

PLACED → ACCEPTED → PREPARING → READY → PICKED


---

## 8. order_items

Stores individual items within an order.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| order_id | BIGINT | Foreign Key → orders(id) |
| menu_item_id | BIGINT | Foreign Key → menu_items(id) |
| quantity | INTEGER | NOT NULL |
| price_at_order | DECIMAL(8,2) | NOT NULL |

### Note
Price is stored at order time to preserve historical accuracy.

---

## 9. audit_logs

Stores audit trails for sensitive actions.

| Column | Type | Constraints |
|------|------|------------|
| id | BIGSERIAL | Primary Key |
| user_id | BIGINT | Foreign Key → users(id) |
| campus_id | BIGINT | Foreign Key → campuses(id), NULL allowed |
| action_type | VARCHAR(50) | NOT NULL |
| entity_type | VARCHAR(50) | NOT NULL |
| entity_id | BIGINT | NOT NULL |
| old_value | JSONB | Nullable |
| new_value | JSONB | Nullable |
| ip_address | VARCHAR(45) | Nullable |
| created_at | TIMESTAMP | DEFAULT current timestamp |

### Rules
- Append-only table
- No UPDATE or DELETE operations allowed

---

## Schema Status

✔ Multi-campus ready  
✔ Role-based access enforced  
✔ Secure onboarding supported  
✔ Audit-compliant  

**This schema is FINAL for Phase 1.**
    
