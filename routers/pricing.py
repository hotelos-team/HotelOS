"""Dynamic pricing endpoints and calculation logic for HotelOS.

Pricing rules:
- Standard room: Rs. 2,500 per night
- Deluxe room: Rs. 4,000 per night
- Suite: Rs. 6,500 per night
- Occupancy below 50%: 1.00x
- Occupancy from 50% through 75%: 1.20x
- Occupancy above 75% through 90%: 1.40x
- Occupancy above 90%: 1.50x
- Friday and Saturday nights: Rs. 500 extra per night
- GST: 12%

There is intentionally no booking lead-time adjustment or VIP discount because
HotelOS is currently designed around on-the-spot bookings.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/pricing", tags=["Pricing"])

# Illustrative project rates, in Indian Rupees (INR).
ROOM_PRICES: dict[str, Decimal] = {
    "standard": Decimal("2500.00"),
    "deluxe": Decimal("4000.00"),
    "suite": Decimal("6500.00"),
}

WEEKEND_SURCHARGE = Decimal("500.00")
GST_RATE = Decimal("0.12")

# Resolve rooms.json relative to the project root, not the terminal's current
# working directory. This makes the API work when started from another folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOMS_FILE = PROJECT_ROOT / "rooms.json"


def _to_money(value: Decimal) -> float:
    """Round a monetary value to 2 decimal places for the JSON response."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def read_rooms() -> list[dict[str, Any]]:
    """Read the room inventory from the existing rooms.json file."""
    try:
        with ROOMS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Room inventory file not found: {ROOMS_FILE.name}",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="rooms.json contains invalid JSON.",
        )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=500,
            detail="rooms.json must contain a list of room categories.",
        )

    return data


def get_occupancy_details() -> dict[str, Any]:
    """Calculate current hotel occupancy from the rooms.json inventory.

    A room counts as occupied only when its status is exactly 'occupied'.
    The actual room entries are counted instead of relying on the '#rooms'
    metadata field, so the result reflects the inventory records.
    """
    room_groups = read_rooms()
    total_rooms = 0
    occupied_rooms = 0

    for group in room_groups:
        rooms = group.get("room", [])
        if not isinstance(rooms, list):
            raise HTTPException(
                status_code=500,
                detail="Each room category must contain a list under 'room'.",
            )

        for room in rooms:
            total_rooms += 1
            if str(room.get("status", "")).strip().lower() == "occupied":
                occupied_rooms += 1

    if total_rooms == 0:
        raise HTTPException(
            status_code=500,
            detail="No rooms are present in rooms.json.",
        )

    occupancy_percent = (occupied_rooms / total_rooms) * 100

    return {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "unoccupied_rooms": total_rooms - occupied_rooms,
        "occupancy_percent": round(occupancy_percent, 2),
    }


def get_occupancy_multiplier(occupancy_percent: float) -> Decimal:
    """Return the multiplier for the supplied occupancy percentage."""
    if not 0 <= occupancy_percent <= 100:
        raise ValueError("occupancy_percent must be between 0 and 100.")

    if occupancy_percent < 50:
        return Decimal("1.00")
    if occupancy_percent <= 75:
        return Decimal("1.20")
    if occupancy_percent <= 90:
        return Decimal("1.40")
    return Decimal("1.50")


def calculate_dynamic_price(
    base_price: float,
    check_in_str: str,
    check_out_str: str,
    occupancy_percent: float,
) -> dict[str, Any]:
    """Calculate an itemized stay price.

    Weekend surcharge applies to Friday and Saturday nights. The checkout date
    itself is not charged because it is the day the guest leaves.

    The function is standalone: it does not read files or call an API. This
    makes the pricing rules straightforward to test independently.
    """
    try:
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("Dates must be valid and use YYYY-MM-DD format.")

    if check_out_date <= check_in_date:
        raise ValueError("check_out must be later than check_in; stay must be at least one night.")

    try:
        base_price_decimal = Decimal(str(base_price))
        occupancy_value = float(occupancy_percent)
    except (ValueError, TypeError, ArithmeticError):
        raise ValueError("base_price and occupancy_percent must be valid numbers.")

    if not base_price_decimal.is_finite() or base_price_decimal <= 0:
        raise ValueError("base_price must be a positive number.")

    if not 0 <= occupancy_value <= 100:
        raise ValueError("occupancy_percent must be between 0 and 100.")

    nights = (check_out_date - check_in_date).days
    base_subtotal = base_price_decimal * nights

    occupancy_multiplier = get_occupancy_multiplier(occupancy_value)
    price_after_occupancy = base_subtotal * occupancy_multiplier
    occupancy_adjustment = price_after_occupancy - base_subtotal

    weekend_dates: list[str] = []
    current_date = check_in_date
    while current_date < check_out_date:
        # weekday(): Monday=0, Friday=4, Saturday=5, Sunday=6.
        if current_date.weekday() in (4, 5):
            weekend_dates.append(current_date.isoformat())
        current_date += timedelta(days=1)

    weekend_surcharge = WEEKEND_SURCHARGE * len(weekend_dates)
    taxable_amount = price_after_occupancy + weekend_surcharge
    gst_amount = taxable_amount * GST_RATE
    final_price = taxable_amount + gst_amount

    return {
        "nights": nights,
        "base_price_per_night": _to_money(base_price_decimal),
        "base_subtotal": _to_money(base_subtotal),
        "occupancy_percent": round(occupancy_value, 2),
        "occupancy_multiplier": float(occupancy_multiplier),
        "occupancy_adjustment": _to_money(occupancy_adjustment),
        "subtotal_after_occupancy": _to_money(price_after_occupancy),
        "weekend_nights": weekend_dates,
        "weekend_surcharge_per_night": _to_money(WEEKEND_SURCHARGE),
        "weekend_surcharge": _to_money(weekend_surcharge),
        "taxable_amount": _to_money(taxable_amount),
        "gst_rate_percent": 12,
        "gst_amount": _to_money(gst_amount),
        "final_price": _to_money(final_price),
        "currency": "INR",
    }


@router.get("/room-types")
def get_room_types() -> dict[str, Any]:
    """Return the supported room categories and their base nightly rates."""
    return {
        "currency": "INR",
        "room_types": [
            {"room_type": room_type, "base_price_per_night": _to_money(price)}
            for room_type, price in ROOM_PRICES.items()
        ],
    }


@router.get("/occupancy")
def get_current_occupancy() -> dict[str, Any]:
    """Return current occupancy calculated from rooms.json."""
    return get_occupancy_details()


@router.get("/quote")
def get_price_quote(
    room_type: str = Query(..., description="standard, deluxe, or suite"),
    check_in: date = Query(..., description="Check-in date in YYYY-MM-DD format"),
    check_out: date = Query(..., description="Check-out date in YYYY-MM-DD format"),
) -> dict[str, Any]:
    """Return an itemized price quote for the requested room and stay."""
    normalized_room_type = room_type.strip().lower()

    if normalized_room_type not in ROOM_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid room_type. Choose one of: {', '.join(ROOM_PRICES)}.",
        )

    if check_out <= check_in:
        raise HTTPException(
            status_code=400,
            detail="check_out must be later than check_in; stay must be at least one night.",
        )

    occupancy = get_occupancy_details()

    try:
        breakdown = calculate_dynamic_price(
            base_price=float(ROOM_PRICES[normalized_room_type]),
            check_in_str=check_in.isoformat(),
            check_out_str=check_out.isoformat(),
            occupancy_percent=occupancy["occupancy_percent"],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "message": "Price quote generated successfully.",
        "room_type": normalized_room_type,
        "occupancy": occupancy,
        "price_breakdown": breakdown,
    }
