from datetime import date, timedelta
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/pricing", tags=["Pricing"])

DATA_DIR = Path(__file__).resolve().parent.parent
ROOMS_FILE = DATA_DIR / "rooms.json"
RESERVATIONS_FILE = DATA_DIR / "reservations.json"

BASE_PRICES = {
    "standard": 2500,
    "deluxe": 4000,
    "suite": 6500,
}
GST_RATE = 0.12
WEEKEND_SURCHARGE = 500


def read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_all_rooms():
    rooms = []
    for category in read_json(ROOMS_FILE):
        rooms.extend(category.get("room", []))
    return rooms


def parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid date in YYYY-MM-DD format",
        )


def occupancy_for_stay(check_in: date, check_out: date, rooms: list) -> float:
    """
    Estimate occupancy for the requested dates using pre-bookings that overlap
    the stay. Rooms already marked occupied without a dated reservation are
    also counted, without counting the same room twice.
    """
    if not rooms:
        raise HTTPException(status_code=503, detail="No room inventory is configured")

    known_room_ids = {room.get("room_id") for room in rooms}
    occupied_ids = {
        room.get("room_id")
        for room in rooms
        if room.get("status") == "occupied" and room.get("room_id") is not None
    }

    for reservation in read_json(RESERVATIONS_FILE):
        room_id = reservation.get("room_id")
        start_value = reservation.get("check_in")
        end_value = reservation.get("check_out")

        if room_id not in known_room_ids or not start_value or not end_value:
            continue

        try:
            booked_in = date.fromisoformat(start_value)
            booked_out = date.fromisoformat(end_value)
        except (TypeError, ValueError):
            continue

        if check_in < booked_out and check_out > booked_in:
            occupied_ids.add(room_id)

    return min(len(occupied_ids) / len(rooms) * 100, 100.0)


def occupancy_multiplier(occupancy: float) -> float:
    if occupancy < 50:
        return 1.0
    if occupancy <= 75:
        return 1.2
    if occupancy <= 90:
        return 1.4
    return 1.5


def calculate_quote(room_type: str, check_in: str, check_out: str):
    normalized_type = room_type.strip().lower()
    if normalized_type not in BASE_PRICES:
        raise HTTPException(
            status_code=400,
            detail="room_type must be Standard, Deluxe, or Suite",
        )

    start = parse_date(check_in, "check_in")
    end = parse_date(check_out, "check_out")
    if end <= start:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    rooms = get_all_rooms()
    occupancy = occupancy_for_stay(start, end, rooms)
    multiplier = occupancy_multiplier(occupancy)

    base_rate = BASE_PRICES[normalized_type]
    nights = (end - start).days
    base_amount = base_rate * nights
    occupancy_adjusted_amount = base_amount * multiplier

    weekend_nights = []
    current = start
    while current < end:
        # Friday=4 and Saturday=5. Checkout date is not charged.
        if current.weekday() in (4, 5):
            weekend_nights.append(current.isoformat())
        current += timedelta(days=1)

    weekend_amount = len(weekend_nights) * WEEKEND_SURCHARGE
    subtotal = occupancy_adjusted_amount + weekend_amount
    gst = round(subtotal * GST_RATE, 2)
    total = round(subtotal + gst, 2)

    return {
        "room_type": normalized_type.title(),
        "check_in": start.isoformat(),
        "check_out": end.isoformat(),
        "nights": nights,
        "base_rate_per_night": base_rate,
        "base_amount": base_amount,
        "projected_occupancy_percent": round(occupancy, 2),
        "occupancy_multiplier": multiplier,
        "amount_after_occupancy": round(occupancy_adjusted_amount, 2),
        "weekend_nights": weekend_nights,
        "weekend_surcharge_per_night": WEEKEND_SURCHARGE,
        "weekend_surcharge_total": weekend_amount,
        "subtotal_before_gst": round(subtotal, 2),
        "gst_rate_percent": GST_RATE * 100,
        "gst_amount": gst,
        "total_price": total,
        "currency": "INR",
    }


@router.get("/quote")
def get_price_quote(
    room_type: str = Query(..., description="Standard, Deluxe, or Suite"),
    check_in: str = Query(..., description="YYYY-MM-DD"),
    check_out: str = Query(..., description="YYYY-MM-DD"),
):
    return calculate_quote(room_type, check_in, check_out)
