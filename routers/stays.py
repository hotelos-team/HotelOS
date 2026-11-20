import json
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/bookings", tags=["Check-in / Check-out"])

DATA_DIR = Path(__file__).resolve().parent.parent
ROOMS_FILE = DATA_DIR / "rooms.json"
RESERVATIONS_FILE = DATA_DIR / "reservations.json"


class StayAction(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=32)


def read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail=f"{path.name} is missing or invalid")


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def find_room(room_groups, room_id):
    for group in room_groups:
        for room in group.get("room", []):
            if room.get("room_id") == room_id:
                return room
    return None


def authorize_staff(x_role: str):
    if x_role.strip().lower() not in {"admin", "manager", "service"}:
        raise HTTPException(
            status_code=403,
            detail="Only admin, manager, or service staff can perform this action",
        )


@router.post("/{reservation_id}/check-in")
def check_in(
    reservation_id: str,
    action: StayAction,
    x_role: str = Header(..., alias="X-Role"),
):
    authorize_staff(x_role)
    reservations = read_json(RESERVATIONS_FILE)
    room_groups = read_json(ROOMS_FILE)

    reservation = next(
        (item for item in reservations
         if str(item.get("reservation_id", item.get("id"))) == reservation_id),
        None,
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if str(reservation.get("user_id")) != action.user_id:
        raise HTTPException(status_code=403, detail="This reservation belongs to another user")

    if reservation.get("status") == "checked_in":
        raise HTTPException(status_code=409, detail="Guest is already checked in")
    if reservation.get("status") == "checked_out":
        raise HTTPException(status_code=409, detail="This reservation has already been checked out")
    if reservation.get("status") not in {"prebooked", "Confirmed", "Paid"}:
        raise HTTPException(status_code=409, detail="Reservation is not eligible for check-in")

    # Do not allow a guest to check in before the booked arrival date or
    # on/after the booked departure date.
    try:
        booked_check_in = date.fromisoformat(reservation["check_in"])
        booked_check_out = date.fromisoformat(reservation["check_out"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=409, detail="Reservation has invalid stay dates")

    today = date.today()
    if today < booked_check_in:
        raise HTTPException(status_code=409, detail="Check-in is not available before the booked check-in date")
    if today >= booked_check_out:
        raise HTTPException(status_code=409, detail="The booked check-out date has passed")

    room = find_room(room_groups, reservation.get("room_id"))
    if room is None:
        raise HTTPException(status_code=404, detail="Room assigned to this reservation was not found")
    if room.get("status") != "empty" or room.get("clean") is not True:
        raise HTTPException(status_code=409, detail="Room is not clean and available for check-in")

    now = datetime.now(timezone.utc).isoformat()
    room["status"] = "occupied"
    room["checkin_time"] = now
    reservation["status"] = "checked_in"
    reservation["actual_check_in"] = now

    write_json(ROOMS_FILE, room_groups)
    write_json(RESERVATIONS_FILE, reservations)

    return {
        "message": "Check-in successful",
        "reservation_id": reservation_id,
        "room_id": reservation["room_id"],
        "status": reservation["status"],
        "checkin_time": now,
    }


@router.post("/{reservation_id}/check-out")
def check_out(
    reservation_id: str,
    action: StayAction,
    x_role: str = Header(..., alias="X-Role"),
):
    authorize_staff(x_role)
    reservations = read_json(RESERVATIONS_FILE)
    room_groups = read_json(ROOMS_FILE)

    reservation = next(
        (item for item in reservations
         if str(item.get("reservation_id", item.get("id"))) == reservation_id),
        None,
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if str(reservation.get("user_id")) != action.user_id:
        raise HTTPException(status_code=403, detail="This reservation belongs to another user")
    if reservation.get("status") != "checked_in":
        raise HTTPException(status_code=409, detail="Guest must be checked in before check-out")

    room = find_room(room_groups, reservation.get("room_id"))
    if room is None:
        raise HTTPException(status_code=404, detail="Room assigned to this reservation was not found")
    if room.get("status") != "occupied":
        raise HTTPException(status_code=409, detail="Room is not marked as occupied")

    now = datetime.now(timezone.utc).isoformat()
    room["status"] = "cleaning"
    room["clean"] = False
    room["checkout_time"] = now
    reservation["status"] = "checked_out"
    reservation["actual_check_out"] = now

    write_json(ROOMS_FILE, room_groups)
    write_json(RESERVATIONS_FILE, reservations)

    return {
        "message": "Check-out successful. Room is now awaiting housekeeping.",
        "reservation_id": reservation_id,
        "room_id": reservation["room_id"],
        "status": reservation["status"],
        "checkout_time": now,
        "room_status": room["status"],
    }
