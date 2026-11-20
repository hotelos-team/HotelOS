# HotelOS

A hotel operations management system built with Python and FastAPI. It includes user/staff access, room inventory, pre-booking, pricing quotes, check-in and check-out.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   python -m pip install fastapi uvicorn python-dotenv pydantic
   ```

3. Copy `important.env.example` to `important.env` and set your own values.
4. Start the API from this folder:

   ```bash
   uvicorn main:app --reload
   ```

5. Open `http://127.0.0.1:8000/docs`.

Do not commit `important.env`; it contains local credentials.

## Main booking and stay endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/bookings/prebook` | Create a pre-booking |
| GET | `/api/bookings` | List bookings (staff role required) |
| GET | `/api/bookings/{user_id}` | Get bookings for one user |
| GET | `/pricing/quote` | Calculate an itemized stay quote |
| POST | `/api/bookings/{reservation_id}/check-in` | Check in a pre-booked guest |
| POST | `/api/bookings/{reservation_id}/check-out` | Check out a checked-in guest |

Check-in and check-out require the `X-Role` header (`admin`, `manager`, or `service`) and a JSON body such as:

```json
{"user_id": "12"}
```

The user ID must match the reservation owner.

## Pricing rules

- Standard: ₹2,500 per night
- Deluxe: ₹4,000 per night
- Suite: ₹6,500 per night
- Occupancy below 50%: 1.0x
- Occupancy from 50% through 75%: 1.2x
- Occupancy above 75% through 90%: 1.4x
- Occupancy above 90%: 1.5x
- Friday and Saturday nights: ₹500 extra per night
- GST: 12%

The quote estimates occupancy for the requested dates from overlapping pre-bookings and currently occupied rooms. Weekend pricing applies to nights stayed, not the checkout date. There is no advance-booking discount or VIP discount.

## Important project notes

- `rooms.json` is the room inventory source used by booking, pricing, and stay operations.
- Creating a pre-booking now calculates the quote from the selected room's category and saves `total_price` plus the full `price_breakdown` in the reservation.
- After check-out, the room is marked `cleaning` and unavailable until housekeeping marks it clean and empty.
- The old `reservations.py` contains earlier, unregistered check-in/check-out functions. The active endpoints are registered through `main.py` from `routers/stays.py`.
