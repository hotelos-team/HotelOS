from fastapi import APIRouter, HTTPException, Header, Query, Path
from routers.pricing import calculate_quote
from pydantic import BaseModel, Field
import json
import uuid
from datetime import date
from pathlib import Path as FilePath

DATA_DIR = FilePath(__file__).resolve().parent

router = APIRouter(tags=["Prebooking"])


class PrebookIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=8)
    room_id: int = Field(...)
    check_in: str = Field(...)
    check_out: str = Field(...)


class UserAuth(BaseModel):
    username: str = Field(min_length=2, max_length=8)
    password: str = Field(min_length=2)


def read_json(filename):
    path = DATA_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_json(filename, data):
    path = DATA_DIR / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def validate_stay_dates(check_in: str, check_out: str):
    try:
        start_date = date.fromisoformat(check_in)
        end_date = date.fromisoformat(check_out)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")

    if end_date <= start_date:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    return start_date, end_date


# 5. Register a new user from prebook
@router.post("/api/prebook/register", status_code=201)
def register_from_prebook(user: UserAuth):
    from main import encrypter, find_largest_id

    users = read_json("users.json")

    for u in users:
        if u.get("username") == user.username:
            raise HTTPException(status_code=409, detail="username already exists")

    new_id = find_largest_id() + 1
    encrypted_pw = encrypter(user.password)

    new_user = {
        "user_id": new_id,
        "username": user.username,
        "password": encrypted_pw,
    }

    users.append(new_user)
    write_json("users.json", users)

    return {"message": "user created", "user_id": new_id, "username": user.username}


# 6. Login to check if username and password match
@router.post("/api/prebook/login", status_code=200)
def login_from_prebook(user: UserAuth):
    from main import encrypter

    users = read_json("users.json")
    encrypted_pw = encrypter(user.password)

    for u in users:
        if u.get("username") == user.username and u.get("password") == encrypted_pw:
            uid = u.get("user_id") or u.get("id")
            return {"message": "login successful", "user_id": uid, "username": u.get("username")}

    raise HTTPException(status_code=401, detail="invalid username or password")


# 1. Create a prebooking
@router.post("/api/bookings/prebook", status_code=201)
def make_prebooking(booking: PrebookIn, x_role: str = Header(...)):
    if x_role.lower() not in ["user", "customer", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="you are not allowed to do this")

    start_date, end_date = validate_stay_dates(booking.check_in, booking.check_out)
    rooms_data = read_json("rooms.json")
    reservations = read_json("reservations.json")

    found_room_type = None
    for category in rooms_data:
        room_list = category.get("room", [])
        for r in room_list:
            if r.get("room_id") == booking.room_id:
                found_room_type = category.get("type")
                break
        if found_room_type is not None:
            break

    if found_room_type is None:
        raise HTTPException(status_code=404, detail="room not found")

    for res in reservations:
        if res.get("room_id") == booking.room_id:
            existing_in = res.get("check_in")
            existing_out = res.get("check_out")
            if existing_in and existing_out:
                try:
                    booked_in = date.fromisoformat(existing_in)
                    booked_out = date.fromisoformat(existing_out)
                except (TypeError, ValueError):
                    continue
                if start_date < booked_out and end_date > booked_in:
                    raise HTTPException(status_code=409, detail="dates are already booked")

    quote = calculate_quote(found_room_type, booking.check_in, booking.check_out)

    new_book = {
        "reservation_id": str(uuid.uuid4()),
        "user_id": booking.user_id,
        "room_id": booking.room_id,
        "room_type": found_room_type,
        "check_in": booking.check_in,
        "check_out": booking.check_out,
        "total_price": quote["total_price"],
        "advance_paid": 0.0,
        "price_breakdown": quote,
        "reservation_status": "Prebooked",
    }

    reservations.append(new_book)
    write_json("reservations.json", reservations)

    return new_book


# 2. Get all reservations (with optional filters)
@router.get("/api/bookings")
def get_bookings(
    status: str = Query(None),
    room_id: int = Query(None),
    x_role: str = Header(...),
):
    if x_role.lower() not in ["admin", "manager", "service"]:
        raise HTTPException(status_code=403, detail="only admins can see this")

    all_res = read_json("reservations.json")
    result = []

    for res in all_res:
        add_it = True
        res_status = res.get("reservation_status") or res.get("status") or ""
        if status is not None and res_status.lower() != status.lower():
            add_it = False
        if room_id is not None and res.get("room_id") != room_id:
            add_it = False

        if add_it:
            result.append(res)

    return result


# 3. Get bookings for a specific user
@router.get("/api/bookings/{user_id}")
def get_user_bookings(user_id: str = Path(..., min_length=1, max_length=8), x_role: str = Header(...)):
    if x_role.strip() == "":
        raise HTTPException(status_code=401, detail="role is missing")

    res = read_json("reservations.json")
    my_books = [r for r in res if str(r.get("user_id")) == str(user_id)]

    if not my_books:
        raise HTTPException(status_code=404, detail="no bookings for this user")

    return my_books


# 4. Delete a user and wipe their bookings
@router.delete("/api/users/{user_id}", status_code=204)
def delete_user_stuff(user_id: str = Path(..., min_length=1, max_length=8), x_role: str = Header(...)):
    if x_role.lower() != "admin":
        raise HTTPException(status_code=403, detail="only admin can delete")

    users = read_json("users.json")
    res = read_json("reservations.json")

    def matches_user(u):
        return (
            u.get("username") == user_id
            or str(u.get("user_id")) == str(user_id)
            or str(u.get("id")) == str(user_id)
        )

    if not any(matches_user(u) for u in users):
        raise HTTPException(status_code=404, detail="user not found")

    new_users = [u for u in users if not matches_user(u)]
    new_res = [r for r in res if str(r.get("user_id")) != str(user_id)]

    write_json("users.json", new_users)
    write_json("reservations.json", new_res)

    return