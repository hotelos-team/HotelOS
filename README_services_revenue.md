# HotelOS — Services and Revenue

This document explains how to integrate and use `services.py` and
`revenue.py` in the HotelOS backend.

## What the modules do

| Module | Purpose |
| --- | --- |
| `services.py` | Handles food, beverage and cleaning requests, displays the menu, and allows staff to update request status. |
| `revenue.py` | Provides an admin-only summary of recorded payments, room charges, completed service charges and outstanding balances. |

Both modules are FastAPI routers. Run them through the main application,
not as standalone Python programs.

## 1. Required files and setup

Keep these files in the same backend directory:

- `main.py`
- `services.py`
- `revenue.py`
- `important.env`
- `users.json`
- `reservations.json`
- `rooms.json`

Service requests are stored in `services.json`, which is created on the
first successful request if it does not already exist.

Use the project's existing Python environment and dependencies.
If the required packages are missing, install them with:

```powershell
python -m pip install fastapi uvicorn python-dotenv
```

Keep the existing authentication configuration in `important.env`.
The modules use `Admin_pass`, `Service_pass`, `a` and `b`.
The values of `a` and `b` must match those used for existing guest passwords.

Do not commit passwords, `important.env` or real guest data.

## 2. Connect the modules to main.py

If these routers are not already registered, add these imports:

```python
from services import router as services_router
from revenue import router as revenue_router
```

After the existing `app = FastAPI(...)`, add:

```python
app.include_router(services_router)
app.include_router(revenue_router)
```

Register each router only once, before any catch-all route or root
static-file mount. Keep the application's existing routes.

## 3. Start the application

Open a terminal in the folder containing `main.py` and run:

```powershell
python -m uvicorn main:app --reload
```

Open Swagger UI:

http://127.0.0.1:8000/docs

Use one server worker because this prototype stores data in JSON files.

## 4. Authentication

Protected endpoints use HTTP Basic authentication.
In Swagger UI, click **Authorize** and enter the appropriate credentials.

| User | Credentials | Permissions |
| --- | --- | --- |
| Guest | Existing guest username and password | Create requests for their own active reservation and view their requests |
| Service staff | Username `Service`, password from `Service_pass` | Create/list requests and update their status |
| Admin | Username `Admin`, password from `Admin_pass` | Staff operations and revenue reports |

Staff usernames are case-sensitive.

## 5. Services endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/services/menu` | View menu items and prices |
| POST | `/api/services/requests` | Create a service request |
| GET | `/api/services/requests` | View requests permitted for the authenticated user |
| PATCH | `/api/services/requests/{service_id}/status` | Update a request's status as staff |

For a service request to be accepted:

- The reservation must exist.
- Its status must be `checked_in`.
- Its associated room must have status `occupied`.
- A guest must own the reservation.

Room records are read from `rooms.json`, using the grouped structure
where each group contains a `room` list.

### View the menu

Execute:

```text
GET /api/services/menu
```

Use the returned item IDs when placing food or beverage requests.

### Create a food request

Open POST `/api/services/requests` in Swagger UI.
Click **Try it out**, enter a body like this, then click **Execute**:

```json
{
  "reservation_id": "R001",
  "category": "food",
  "items": [
    {
      "item_id": "veg_sandwich",
      "quantity": 2
    }
  ],
  "notes": "Please deliver to the room."
}
```

Replace `R001` with an existing checked-in reservation ID.

The server calculates the price. Do not send your own total.
Each quantity must be an integer from 1 to 20.

For a beverage request, use category `beverage` and an appropriate
menu item ID, such as `tea`.

### Create a cleaning request

```json
{
  "reservation_id": "R001",
  "category": "cleaning",
  "guest_in_room": false,
  "permission_to_enter": true,
  "notes": "Please clean after 2 PM."
}
```

Cleaning is free in this implementation.
The presence and permission fields are recorded for staff.

This endpoint handles requests during an active stay.
It does not automatically arrange cleaning after checkout.

### View requests

Execute:

```text
GET /api/services/requests
```

To filter by status, use:

```text
GET /api/services/requests?status=pending
```

Supported statuses are:

- `pending`
- `in_progress`
- `completed`
- `cancelled`

### Update a request's status

Authenticate as `Service` or `Admin`.

Copy the request's `service_id` into the PATCH endpoint's path parameter.

To start work, send:

```json
{
  "status": "in_progress"
}
```

To finish it, send:

```json
{
  "status": "completed"
}
```

Allowed transitions:

| Current status | Allowed next statuses |
| --- | --- |
| `pending` | `in_progress`, `cancelled` |
| `in_progress` | `completed`, `cancelled` |
| `completed` | None |
| `cancelled` | None |

A pending request cannot move directly to completed.

Completing a service records a billable charge.
It does not record receipt of payment.

## 6. Revenue endpoint

Authenticate as `Admin` and execute:

```text
GET /api/revenue/summary
```

The report reads reservation and service data.
It does not collect payments or modify reservation payment fields.

### Required payment fields

Reservations included in the report need these nonnegative integer fields:

| Field | Meaning |
| --- | --- |
| `room_total_paise` | Full agreed room charge for the entire stay |
| `room_paid_paise` | Cumulative room payments received, net of refunds |
| `service_paid_paise` | Cumulative service payments received, net of refunds |

All amounts are in paise:

```text
₹1 = 100 paise
₹3,000 = 300000 paise
```

Example reservation payment fields:

```json
{
  "room_total_paise": 1000000,
  "room_paid_paise": 300000,
  "service_paid_paise": 0
}
```

Add these fields to the relevant reservation record.
Do not replace the whole record or remove its other fields.

The booking/payment code must maintain these values.
The report does not assume payment was received simply because a
reservation is checked in or checked out.

### Payment policy and balances

The room payment targets are:

- 30% at check-in.
- The remaining 70% at checkout.

Service charges are tracked separately.

```text
Balance = full room charge + completed service charges
          - room payments received - service payments received
```

A positive balance is an amount still due.
An overpayment is reported as credit.

Example:

| Item | Amount |
| --- | ---: |
| Full room charge | ₹10,000 |
| Room payment received | ₹3,000 |
| Completed service charges | ₹240 |
| Service payment received | ₹0 |
| Remaining balance | ₹7,240 |

Here, recorded collections are ₹3,000, not ₹3,240:
the ₹240 service has been charged but has not yet been paid.

### Reading the report

- Only completed services contribute to billed service charges.
- Pending/in-progress services are estimates.
- Cancelled services contribute no charge.
- Invalid reservation data appears in `excluded_reservations`.
- Services without a matching reservation appear in `orphan_service_ids`.
- If `report_complete` is false, investigate these entries before relying
  on the totals.

The report does not calculate profit or provide date filtering.

## 7. Quick verification

1. Start the application and open `/docs`.
2. Confirm that the services and revenue endpoints appear.
3. View the menu.
4. Authenticate as a guest with a checked-in reservation and occupied room.
5. Create a food request.
6. Authenticate as staff and move it from pending to in_progress to completed.
7. Authenticate as Admin and view the revenue summary.
8. Confirm that completed service charges increase, while collected
   payments remain unchanged until the payment workflow records payment.

## 8. Troubleshooting

| Problem | What to check |
| --- | --- |
| Endpoints missing | Router registration in `main.py`; correct application launched |
| 401 | Username, password and authentication configuration |
| 403 | User role or reservation ownership |
| 404 | Reservation, room or service ID |
| 409 | Reservation/room status or invalid request-status transition |
| 422 | Request fields, category and integer quantities |
| 503 | Missing/corrupt data, configuration errors or duplicate reservation IDs |
| Incomplete revenue report | Excluded reservations and orphan service records |