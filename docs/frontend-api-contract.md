# Frontend-Backend API Contract

**Base URL:** `http://localhost:8080`
**Auth:** Stateless JWT via `Authorization: Bearer <token>` header
**Content-Type:** `application/json`

---

## Table of Contents

1. [Auth Pages](#1-auth-pages)
2. [Student Pages](#2-student-pages)
3. [Manager Pages](#3-manager-pages)
4. [Admin Pages](#4-admin-pages)
5. [SuperAdmin Pages](#5-superadmin-pages)
6. [Shared: Notifications](#6-shared-notifications)
7. [Data Models / DTOs](#7-data-models--dtos)

---

## 1. Auth Pages

### 1.1 Login

| Field | Value |
|-------|-------|
| **Page** | `/login` |
| **Endpoint** | `POST /api/auth/login` |
| **Auth** | Public (no JWT) |
| **Role** | None |

**Request:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "token": "string (JWT)",
  "role": "STUDENT | MANAGER | ADMIN | SUPERADMIN",
  "name": "string",
  "email": "string",
  "id": "string (userId)",
  "accountStatus": "ACTIVE | WARNING | SUSPENDED | PENDING_VERIFICATION",
  "pendingPenalty": "string (decimal)",
  "noShowCount": "string (int)",
  "campusId": "string | null"
}
```

**Error (401):**
```json
{
  "message": "Invalid email or password"
}
```

**Post-login routing by role:**
- `STUDENT` -> `/student/home`
- `MANAGER` -> `/manager/dashboard`
- `ADMIN` -> `/admin/dashboard`
- `SUPERADMIN` -> `/superadmin/dashboard`

---

### 1.2 Register (Student)

| Field | Value |
|-------|-------|
| **Page** | `/register` |
| **Endpoint** | `POST /api/auth/register` |
| **Auth** | Public |
| **Role** | None |

**Request:**
```json
{
  "fullName": "string",
  "email": "string (campus email - domain auto-detects campus)",
  "password": "string"
}
```

**Response (200):**
```json
{
  "message": "OTP sent to your email",
  "email": "string",
  "status": "PENDING_VERIFICATION"
}
```

---

### 1.3 Verify Email OTP

| Field | Value |
|-------|-------|
| **Page** | Inline on register screen |
| **Endpoint** | `POST /api/auth/verify-email` |
| **Auth** | Public |

**Request:**
```json
{
  "email": "string",
  "otp": "string (6 digits)"
}
```

**Response (200):** Same shape as Login response (token, role, name, etc.)

---

### 1.4 Resend OTP

| Field | Value |
|-------|-------|
| **Endpoint** | `POST /api/auth/resend-otp` |
| **Auth** | Public |

**Request:**
```json
{
  "email": "string"
}
```

**Response (200):**
```json
{
  "message": "OTP resent successfully"
}
```

---

### 1.5 Apply as Campus Admin

| Field | Value |
|-------|-------|
| **Page** | `/apply-admin` |
| **Endpoint** | `POST /api/admin-applications` |
| **Auth** | Public |

**Request:**
```json
{
  "fullName": "string",
  "applicantEmail": "string",
  "designation": "string",
  "idCardPhotoUrl": "string",
  "campusName": "string",
  "campusLocation": "string",
  "campusEmailDomain": "string (e.g. 'vit.edu')"
}
```

**Response (201):** `AdminApplication` object

---

### 1.6 Apply as Outlet Manager

| Field | Value |
|-------|-------|
| **Page** | `/apply-outlet` |
| **Endpoint** | `POST /api/outlet-applications` |
| **Auth** | Public |

**Request:**
```json
{
  "managerName": "string",
  "managerEmail": "string",
  "outletName": "string",
  "outletDescription": "string",
  "avgPrepTime": "int (minutes)",
  "licenseDocUrl": "string",
  "outletPhotoUrl": "string | null",
  "campusId": "int"
}
```

**Response (201):** `OutletApplication` object

---

## 2. Student Pages

### 2.1 Home (Outlet Feed)

| Field | Value |
|-------|-------|
| **Page** | `/student/home` |
| **Endpoint** | `GET /api/outlets/campus/{campusId}` |
| **Auth** | JWT required |
| **Role** | STUDENT |

**Response (200):** `List<Outlet>`

---

### 2.2 Outlet Detail

| Field | Value |
|-------|-------|
| **Page** | `/student/outlet/:id` |

**Sub-endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/outlets/{id}` | GET | Outlet details |
| `GET /api/menu-items?outletId={id}` | GET | Available menu items |
| `GET /api/slots?outletId={id}` | GET | Today's pickup slots |
| `GET /api/menu-items/recommendations?outletId={id}` | GET | ML-powered food recommendations |

**Response - Outlet:** `Outlet` object
**Response - Menu:** `List<MenuItem>`
**Response - Slots:** `List<PickupSlot>`
**Response - Recommendations:** `List<MenuItem>`

---

### 2.3 Cart & Checkout

| Field | Value |
|-------|-------|
| **Page** | `/student/cart` then `/student/checkout` |

**Place Order:**

| Endpoint | Method | Auth | Role |
|----------|--------|------|------|
| `POST /api/orders` | POST | JWT | STUDENT |

**Request:**
```json
{
  "studentId": "int",
  "outletId": "int",
  "slotId": "int",
  "paymentMode": "ONLINE | COD",
  "items": [
    {
      "menuItemId": "int",
      "quantity": "int"
    }
  ]
}
```

**Response (200):** `Order` object

**Initiate Payment (ONLINE only):**

| Endpoint | Method |
|----------|--------|
| `POST /api/payments/initiate/order/{orderId}` | POST |

**Response:**
```json
{
  "rzpOrderId": "string",
  "amount": "int (paise)",
  "currency": "INR",
  "keyId": "string"
}
```

**Verify Payment:**

| Endpoint | Method |
|----------|--------|
| `POST /api/payments/verify/order` | POST |

**Request:**
```json
{
  "razorpayOrderId": "string",
  "razorpayPaymentId": "string",
  "razorpaySignature": "string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment verified",
  "pickupOtp": "string (6 digits)",
  "verifiedAt": "string (ISO datetime)"
}
```

---

### 2.4 Order Tracking (SSE)

| Field | Value |
|-------|-------|
| **Page** | `/student/order/:id/tracking` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/orders/{id}` | GET | Order detail + items |
| `GET /api/orders/{id}/events` | GET (SSE) | Real-time status stream |

**SSE Event Format:** `text/event-stream`
**Auto-closes on:** PICKED, CANCELLED, EXPIRED

---

### 2.5 My Orders

| Field | Value |
|-------|-------|
| **Page** | `/student/orders` |
| **Endpoint** | `GET /api/orders/student/{studentId}` |
| **Auth** | JWT, Role: STUDENT |

**Response (200):** `List<OrderDetailResponse>`

**Repeat Order:** `POST /api/orders/repeat/{orderId}`
**Cancel Order:** `POST /api/orders/{id}/cancel`

---

### 2.6 Profile

| Field | Value |
|-------|-------|
| **Page** | `/student/profile` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/users/me` | GET | User profile |
| `PATCH /api/users/me/profile` | PATCH | Update name/phone |
| `PATCH /api/users/me/password` | PATCH | Change password |

**PATCH Profile Request:**
```json
{
  "fullName": "string",
  "phone": "string"
}
```

**PATCH Password Request:**
```json
{
  "currentPassword": "string",
  "newPassword": "string"
}
```

---

### 2.7 Penalty

| Field | Value |
|-------|-------|
| **Page** | `/student/penalty` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/penalties/me` | GET | Current user penalty status |
| `POST /api/penalties/{userId}/pay` | POST | Pay penalty (CASH) |

**Response - Penalty Status:**
```json
{
  "noShowCount": "int",
  "pendingPenaltyAmount": "double",
  "accountStatus": "string"
}
```

---

### 2.8 Rate Order

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/ratings/order/{orderId}` | POST | Rate 1-5 stars |

**Request:**
```json
{
  "stars": "int (1-5)",
  "comment": "string | null"
}
```

---

## 3. Manager Pages

### 3.1 Outlet Setup

| Field | Value |
|-------|-------|
| **Page** | `/manager/setup` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/outlets/mine` | GET | Manager's own outlet |
| `POST /api/menu-items` | POST | Add menu item |
| `POST /api/outlets/{id}/launch` | POST | Launch outlet (PENDING_LAUNCH -> ACTIVE) |

**POST Menu Item Request:**
```json
{
  "outletId": "int",
  "name": "string",
  "price": "double",
  "prepTime": "int (minutes)",
  "photoUrl": "string | null"
}
```

---

### 3.2 Dashboard (Active Orders)

| Field | Value |
|-------|-------|
| **Page** | `/manager/dashboard` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/orders/outlet/{outletId}` | GET | Orders for outlet |
| `PATCH /api/orders/{id}/status` | PATCH | Advance status |
| `POST /api/orders/{id}/pickup` | POST | Confirm pickup via OTP |
| `POST /api/outlets/{id}/toggle` | POST | Toggle open/close |

**PATCH Status Request:**
```json
{
  "status": "PREPARING | READY"
}
```

**POST Pickup Request:**
```json
{
  "otp": "string (6 digits)"
}
```

**Counter Order:** `POST /api/manager/orders/counter`
```json
{
  "customerName": "string",
  "paymentMode": "ONLINE | COD",
  "slotId": "int | null",
  "items": [{ "menuItemId": "int", "quantity": "int" }]
}
```

---

### 3.3 Menu Management

| Field | Value |
|-------|-------|
| **Page** | `/manager/menu` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/menu-items/all?outletId={id}` | GET | All items (incl. out of stock) |
| `POST /api/menu-items` | POST | Add item |
| `PATCH /api/menu-items/{id}` | PATCH | Edit item |
| `DELETE /api/menu-items/{id}` | DELETE | Remove item |
| `PATCH /api/menu-items/{id}/availability` | PATCH | Toggle availability |

**PATCH Availability Request:**
```json
{
  "available": "boolean"
}
```

---

### 3.4 Slot Management

| Field | Value |
|-------|-------|
| **Page** | `/manager/slots` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/slots?outletId={id}` | GET | Today's slots |
| `POST /api/slots` | POST | Create slot |
| `DELETE /api/slots/{id}` | DELETE | Delete slot |
| `PATCH /api/slots/{id}/capacity` | PATCH | Update max orders |

**POST Slot Request:**
```json
{
  "outletId": "int",
  "startTime": "string (HH:mm)",
  "endTime": "string (HH:mm)",
  "maxOrders": "int"
}
```

---

### 3.5 Ledger & Analytics

| Field | Value |
|-------|-------|
| **Page** | `/manager/ledger` and `/manager/analytics` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/manager/orders/ledger?date=YYYY-MM-DD` | GET | Daily ledger |
| `GET /api/manager/orders/ledger/summary?date=YYYY-MM-DD` | GET | Sales summary |
| `GET /api/outlets/analytics/weekly` | GET | 7-day revenue chart |
| `GET /api/payouts/my-outlet` | GET | Payout history |

---

### 3.6 Operating Hours & Bank Details

| Endpoint | Method | Description |
|----------|--------|-------------|
| `PATCH /api/outlets/{id}/hours` | PATCH | Set operating hours |
| `PATCH /api/payouts/mine/bank-details` | PATCH | Save bank details |

**PATCH Hours Request:**
```json
{
  "openingTime": "string (HH:mm)",
  "closingTime": "string (HH:mm)"
}
```

**PATCH Bank Details Request:**
```json
{
  "bankAccountNumber": "string",
  "bankIfscCode": "string",
  "bankAccountHolderName": "string"
}
```

---

## 4. Admin Pages

### 4.1 Dashboard

| Field | Value |
|-------|-------|
| **Page** | `/admin/dashboard` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/outlets/campus/{campusId}/all` | GET | All campus outlets |
| `GET /api/outlet-applications/pending` | GET | Pending applications |

---

### 4.2 Outlet Application Review

| Field | Value |
|-------|-------|
| **Page** | `/admin/outlet-applications` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/outlet-applications/pending` | GET | Pending apps |
| `GET /api/outlet-applications/all` | GET | All apps (history) |
| `GET /api/outlet-applications/{id}/verification-report` | GET | Auto verification report |
| `PATCH /api/outlet-applications/{id}/approve` | PATCH | Approve |
| `PATCH /api/outlet-applications/{id}/reject` | PATCH | Reject |

**Approve Request:**
```json
{
  "temporaryPassword": "string",
  "message": "string | null"
}
```

**Reject Request:**
```json
{
  "rejectionReason": "string",
  "message": "string | null"
}
```

---

### 4.3 Outlet Management

| Field | Value |
|-------|-------|
| **Page** | `/admin/outlets` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/outlets/campus/{campusId}/all` | GET | All campus outlets |
| `POST /api/outlets/{id}/suspend` | POST | Suspend outlet |
| `POST /api/outlets/{id}/reactivate` | POST | Reactivate outlet |

---

### 4.4 Penalty Management

| Field | Value |
|-------|-------|
| **Page** | `/admin/penalties` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/penalties/{userId}/status` | GET | Student penalty status |
| `POST /api/penalties/{userId}/waive` | POST | Waive penalty |

---

## 5. SuperAdmin Pages

### 5.1 Dashboard (Admin Applications)

| Field | Value |
|-------|-------|
| **Page** | `/superadmin/dashboard` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/admin-applications` | GET | Pending applications |
| `GET /api/admin-applications/all` | GET | All applications |
| `PATCH /api/admin-applications/{id}/approve` | PATCH | Approve |
| `PATCH /api/admin-applications/{id}/reject` | PATCH | Reject |

**Approve Request:**
```json
{
  "temporaryPassword": "string",
  "message": "string | null"
}
```

**Reject Request:**
```json
{
  "rejectionReason": "string",
  "message": "string | null"
}
```

---

### 5.2 Campus List & Detail

| Field | Value |
|-------|-------|
| **Page** | `/superadmin/campuses` and `/superadmin/campus/:id` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/campuses` | GET | All campuses (public) |
| `GET /api/campuses/{id}` | GET | Campus detail |
| `GET /api/campuses/{id}/outlets` | GET | Campus outlets |
| `POST /api/campuses/{id}/deactivate` | POST | Deactivate campus |
| `POST /api/campuses/{id}/reactivate` | POST | Reactivate campus |

---

## 6. Shared: Notifications

| Field | Value |
|-------|-------|
| **Page** | Available from all role dashboards |
| **Auth** | JWT required (any role) |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/notifications` | GET | All notifications |
| `GET /api/notifications/unread` | GET | Unread only |
| `GET /api/notifications/unread-count` | GET | Count for badge |
| `PATCH /api/notifications/{id}/read` | PATCH | Mark one read |
| `PATCH /api/notifications/read-all` | PATCH | Mark all read |

**Notification Types:**
- `ORDER_PLACED`, `ORDER_READY`, `ORDER_EXPIRED`, `ORDER_CANCELLED`
- `PENALTY_APPLIED`
- `OUTLET_APP_APPROVED`, `OUTLET_APP_REJECTED`
- `ADMIN_APP_APPROVED`, `ADMIN_APP_REJECTED`
- `VERIFICATION_DONE`

---

## 7. Data Models / DTOs

### AuthResponse
```json
{
  "token": "string",
  "role": "string",
  "name": "string",
  "email": "string",
  "id": "string",
  "accountStatus": "string",
  "pendingPenalty": "string",
  "noShowCount": "string",
  "campusId": "string | null"
}
```

### Outlet
```json
{
  "id": "int",
  "name": "string",
  "status": "PENDING_LAUNCH | ACTIVE | CLOSED | SUSPENDED | DELETED",
  "avgPrepTime": "int",
  "photoUrl": "string | null",
  "launchedAt": "string | null",
  "createdAt": "string"
}
```

### MenuItem
```json
{
  "id": "int",
  "name": "string",
  "price": "double",
  "prepTime": "int",
  "photoUrl": "string | null",
  "isAvailable": "boolean",
  "createdAt": "string",
  "outletId": "int | null"
}
```

### PickupSlot
```json
{
  "id": "int",
  "outletId": "int",
  "startTime": "string (ISO datetime)",
  "endTime": "string (ISO datetime)",
  "maxOrders": "int",
  "currentOrders": "int"
}
```

### Order
```json
{
  "id": "int",
  "status": "PLACED | PREPARING | READY | PICKED | EXPIRED | CANCELLED",
  "totalAmount": "double",
  "paymentMode": "ONLINE | COD",
  "paymentStatus": "PENDING | PAID | FAILED | REFUND_PENDING | REFUND_INITIATED",
  "readyAt": "string (ISO datetime)",
  "expiresAt": "string (ISO datetime)",
  "createdAt": "string"
}
```

### Campus
```json
{
  "id": "int",
  "name": "string",
  "location": "string",
  "emailDomain": "string",
  "status": "ACTIVE | INACTIVE",
  "createdAt": "string"
}
```

### OutletApplication
```json
{
  "id": "int",
  "managerName": "string",
  "managerEmail": "string",
  "outletName": "string",
  "outletDescription": "string | null",
  "avgPrepTime": "int",
  "licenseDocUrl": "string",
  "outletPhotoUrl": "string | null",
  "status": "PENDING | APPROVED | REJECTED",
  "rejectionReason": "string | null",
  "attemptNumber": "int",
  "createdAt": "string"
}
```

### AdminApplication
```json
{
  "id": "int",
  "fullName": "string",
  "applicantEmail": "string",
  "designation": "string",
  "idCardPhotoUrl": "string",
  "campusName": "string",
  "campusLocation": "string",
  "campusEmailDomain": "string",
  "status": "PENDING | APPROVED | REJECTED",
  "rejectionReason": "string | null",
  "attemptNumber": "int",
  "createdAt": "string"
}
```

### AppNotification
```json
{
  "id": "int",
  "title": "string",
  "message": "string",
  "type": "string",
  "isRead": "boolean",
  "createdAt": "string"
}
```
