# Flutter Integration Notes (Legacy Reference)

This document captures reusable business logic, API schemas, model definitions,
validation rules, and integration patterns from the Flutter/Dart frontend before
deletion. Use this as a reference when building the React frontend.

---

## 1. Authentication Flow

### Token Storage
- **JWT Token:** Stored in `flutter_secure_storage` (encrypted)
- **User Metadata:** Stored in `SharedPreferences` (unencrypted)
  - Keys: `role`, `name`, `email`, `userId`, `campusId`, `accountStatus`, `pendingPenalty`, `noShowCount`

### Auth Interceptor (Dio)
- Every request auto-attaches `Authorization: Bearer <token>` header
- On 401 response: clears all storage, redirects to `/login`

### Role-Based Routing
- Unauthenticated users -> `/login`
- `STUDENT` -> `/student/home`
- `MANAGER` -> `/manager/dashboard`
- `ADMIN` -> `/admin/dashboard`
- `SUPERADMIN` -> `/superadmin/dashboard`
- Public routes: `/login`, `/register`, `/apply-admin`, `/apply-outlet`

### Registration Flow
1. Student submits `POST /api/auth/register` with campus email
2. Backend auto-detects campus from email domain
3. OTP sent to email
4. Student submits `POST /api/auth/verify-email` with 6-digit OTP
5. Account activated, JWT returned

---

## 2. API Models (Dart -> JSON Schema)

### AuthResponse
| Field | Type | Notes |
|-------|------|-------|
| token | String | JWT |
| role | String | STUDENT/MANAGER/ADMIN/SUPERADMIN |
| name | String | Full name |
| email | String | Campus email |
| id | String | User ID (as string) |
| accountStatus | String | ACTIVE/WARNING/SUSPENDED/PENDING_VERIFICATION |
| pendingPenalty | String | Decimal amount (as string) |
| noShowCount | String | Integer (as string) |
| campusId | String? | Null for SUPERADMIN |

### Outlet
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| name | String | |
| status | String | PENDING_LAUNCH/ACTIVE/CLOSED/SUSPENDED/DELETED |
| avgPrepTime | int | Minutes |
| photoUrl | String? | |
| launchedAt | String? | ISO datetime |
| createdAt | String | ISO datetime |

### MenuItem
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| name | String | |
| price | double | |
| prepTime | int | Minutes |
| photoUrl | String? | |
| isAvailable | bool | Default true |
| createdAt | String | ISO datetime |
| outletId | int? | |

### PickupSlot
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| outletId | int | |
| startTime | String | ISO datetime -> formatted to "H:mm AM/PM" |
| endTime | String | ISO datetime -> formatted to "H:mm AM/PM" |
| maxOrders | int | |
| currentOrders | int | Default 0 |
| isFull | bool | Computed: currentOrders >= maxOrders |

### Order
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| status | String | PLACED/PREPARING/READY/PICKED/EXPIRED/CANCELLED |
| totalAmount | double | |
| paymentMode | String | ONLINE/COD |
| paymentStatus | String | PENDING/PAID/FAILED/REFUND_PENDING/REFUND_INITIATED |
| readyAt | String | ISO datetime |
| expiresAt | String | ISO datetime |
| createdAt | String | ISO datetime |

### Campus
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| name | String | |
| location | String | |
| emailDomain | String | e.g. "vit.edu" |
| status | String | ACTIVE/INACTIVE |
| createdAt | String | ISO datetime |

### OutletApplication
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| managerName | String | |
| managerEmail | String | |
| outletName | String | |
| outletDescription | String? | |
| avgPrepTime | int | |
| licenseDocUrl | String | |
| outletPhotoUrl | String? | |
| status | String | PENDING/APPROVED/REJECTED |
| rejectionReason | String? | |
| attemptNumber | int | Max 3 |
| createdAt | String | |

### AdminApplication
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| fullName | String | |
| applicantEmail | String | |
| designation | String | |
| idCardPhotoUrl | String | |
| campusName | String | |
| campusLocation | String | |
| campusEmailDomain | String | |
| status | String | PENDING/APPROVED/REJECTED |
| rejectionReason | String? | |
| attemptNumber | int | Max 3 |
| createdAt | String | |

### AppNotification
| Field | Type | Notes |
|-------|------|-------|
| id | int | |
| title | String | |
| message | String | |
| type | String | ORDER_PLACED/ORDER_READY/ORDER_EXPIRED/PENALTY/OUTLET_APPROVED/OUTLET_REJECTED/ADMIN_APPROVED |
| isRead | bool | |
| createdAt | String | |

---

## 3. Business Logic Patterns

### Cart Management
- Cart is per-outlet: switching outlets clears the cart
- Quantity: increment/decrement with remove at 0
- Total computed client-side: `sum(item.price * quantity)`
- Slot selection is required before checkout
- Payment mode: ONLINE (Razorpay) or COD

### Order Status Flow
```
PLACED -> PREPARING -> READY -> PICKED
                                  |
              +-------------------+
              |                   |
          EXPIRED             CANCELLED
```

### Order Source
- `PLATFORM`: Student app order
- `COUNTER`: Manager walk-in order (no student account needed)

### Penalty System
- Orders stuck in PLACED/PREPARING past expiresAt -> EXPIRED (no penalty, outlet's fault)
- Orders in READY past expiresAt -> genuine no-show, penalty charged
- Penalty = base 50 * (1 - avgDemandScore)
- After 3 no-shows: account status -> WARNING (blocked until penalties cleared)
- Penalty can be paid via CASH (manager confirms) or ONLINE (Razorpay)

### Outlet Status Flow
```
PENDING_LAUNCH -> (manager launches) -> ACTIVE <-> CLOSED (manager toggle)
ACTIVE/CLOSED -> SUSPENDED (admin) -> ACTIVE (admin reactivates)
Any -> DELETED (admin, permanent soft-delete)
```

### Notification Types & Colors (from Flutter)
| Type | Icon | Color |
|------|------|-------|
| ORDER_PLACED | receipt_long | Blue |
| ORDER_READY | check_circle | Green |
| ORDER_EXPIRED | timer_off | Red |
| PENALTY | warning_amber | Orange |
| OUTLET_APPROVED | storefront | Green |
| OUTLET_REJECTED | cancel | Red |
| ADMIN_APPROVED | verified_user | Green |

### Time Formatting
- PickupSlot times: parsed from ISO datetime, formatted to "H:mm AM/PM"
- Notifications: relative time ("Just now", "5m ago", "2h ago", "3d ago")
- Order countdown: live timer showing time until ready, then time until expiry

---

## 4. Payment Integration (Razorpay)

### Flow
1. Student places order -> `POST /api/orders`
2. If ONLINE: `POST /api/payments/initiate/order/{orderId}` -> returns `rzpOrderId` + `keyId`
3. Flutter opens Razorpay checkout sheet with these values
4. On success: `POST /api/payments/verify/order` with signature
5. Backend verifies HMAC-SHA256, marks order PAID, generates 6-digit pickup OTP
6. Student shows OTP to manager for pickup confirmation

### Dev Mode
- `POST /api/payments/order/{orderId}/simulate` bypasses Razorpay entirely
- Useful for local testing

---

## 5. SSE (Server-Sent Events) for Order Tracking

- Endpoint: `GET /api/orders/{id}/events` (text/event-stream)
- Uses Redis pub/sub for horizontal scaling
- Auto-closes on terminal states: PICKED, CANCELLED, EXPIRED
- 10-minute timeout
- No WebSocket endpoints exist

---

## 6. ML Service Integration

All ML calls go through Spring Boot's `MLClient`, not directly to Python.

| Feature | Backend Endpoint | Python Endpoint | Fallback |
|---------|-----------------|-----------------|----------|
| Food recommendations | `/api/ml/recommend` | `POST /recommend/food` | Empty list |
| Wait time prediction | `/api/ml/wait-time` | `POST /predict/wait-time` | 20 min |
| Slot demand forecast | `/api/ml/slot-forecast` | `GET /forecast/slot-demand` | Empty map |
| Menu analytics | `/api/ml/menu-analytics` | `GET /analytics/menu-performance` | Empty list |
| Demand scoring | (internal) | `POST /predict/demand-score` | 0.5 |
| No-show risk | (internal) | `POST /predict/no-show-risk` | 0.5 |

All ML calls have graceful degradation with safe fallback values.

---

## 7. Key UI Patterns to Recreate

### Student Home Screen
- Greeting with student name
- Penalty warning banner (if WARNING status)
- Outlet cards: photo, name, prep time, status badge
- Floating cart FAB when items in cart

### Outlet Detail Screen
- Collapsible header with outlet photo
- Horizontal pickup slot selector with capacity ("X left")
- Menu items: photo, name, prep time, price, ADD/+/- button
- Out-of-stock items grayed out
- Bottom bar: cart total + checkout button

### Manager Dashboard
- Auto-polls orders every 30 seconds
- Active orders with status-advancement buttons
- PLACED -> "Mark Preparing" -> PREPARING -> "Mark Ready" -> READY -> "Mark Picked"

### Admin Dashboard
- Summary cards: Total Outlets, Active, Pending Applications
- Quick action tiles with badge counts

### SuperAdmin Dashboard
- TabBarView: Pending / All Applications
- Approve with temporary password
- Reject with reason + attempt warning

---

## 8. Validation Rules

### Registration
- Full name: required
- Email: must be valid campus email (domain auto-detected)
- Password: required
- Confirm password must match

### Admin Application
- Max 3 attempts per email
- Email domain must match claimed campus

### Outlet Application
- Max 3 attempts per email
- Required: managerName, managerEmail, outletName, avgPrepTime, licenseDocUrl, campusId
- Optional: outletDescription, outletPhotoUrl

### Menu Item
- Required: name, price, prepTime
- Optional: photoUrl

### Pickup Slot
- Required: startTime, endTime, maxOrders
- startTime must be before endTime
- maxOrders must be positive

### Order
- Required: studentId, outletId, slotId, paymentMode, items[]
- Each item: menuItemId, quantity
- Outlet must be ACTIVE
- Slot must have capacity
- Daily limit: 3 orders per student per outlet
- Student must not be WARNING/SUSPENDED

---

## 9. State Management (Flutter Riverpod -> React equivalents)

| Flutter Riverpod | React Equivalent |
|-----------------|------------------|
| `FutureProvider<T>` | `useQuery` (React Query) |
| `NotifierProvider<T>` | Zustand store |
| `ref.invalidate()` | `queryClient.invalidateQueries()` |
| `ref.watch()` | `useStore()` or `useQuery()` |
| `ref.read()` | `useStore.getState()` |

### Stores to Recreate
1. **authStore** (Zustand + persist): token, role, userId, userName, userEmail, campusId, accountStatus, pendingPenalty
2. **cartStore** (Zustand): items, outletId, selectedSlotId, paymentMethod, addItem, removeItem, clearCart, total, itemCount

---

## 10. Error Handling Patterns

### API Client
- 401 -> clear storage, redirect to login
- Other errors -> propagate to UI

### UI Error States
- Loading spinner during fetch
- Error message with retry button
- Empty state with icon + message

### Order Placement
- try/catch around API call
- Loading state during submission
- Navigate to confirmation on success
- Show toast/snackbar on error
