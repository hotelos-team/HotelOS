from fastapi import APIRouter, HTTPException, Header, Query, Path
from routers.pricing import calculate_quote
from pydantic import BaseModel, Field
import json
import uuid
from datetime import date
from pathlib import Path as FilePath

DATA_DIR = FilePath(__file__).resolve().parent

# setting up router so it doesn't clutter up the main file
router = APIRouter()

# my input model for the post request
# using Field to make sure the user_id is between 2 and 8 characters long!
class PrebookIn(BaseModel):
    user_id: str = Field(min_length=2, max_length=8)
    room_id: int = Field(...) 
    check_in: str = Field(...)
    check_out: str = Field(...)

# safe function to read json so my server doesnt crash if the file is missing or weird
def read_json(filename):
    path = DATA_DIR / filename
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_json(filename, data):
    path = DATA_DIR / filename
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def validate_stay_dates(check_in, check_out):
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD format")
    if end <= start:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")
    return start, end

# 1. create a prebooking
@router.post("/api/bookings/prebook", status_code=201)
def make_prebooking(booking: PrebookIn, x_role: str = Header(...)):
    # checking permissions to make sure they are allowed
    if x_role not in ["customer", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="you are not allowed to do this")

    start_date, end_date = validate_stay_dates(booking.check_in, booking.check_out)
    rooms_data = read_json('rooms.json')
    reservations = read_json('reservations.json')

    # we need a double loop because the rooms are hidden inside categories like 'deluxe'
    found_room_type = None
    for category in rooms_data:
        # get the list of rooms inside this specific category
        room_list = category.get("room", [])
        for r in room_list:
            if r.get("room_id") == booking.room_id:
                found_room_type = category.get("type")
                break
        if found_room_type is not None:
            break
    
    if found_room_type is None:
        raise HTTPException(status_code=404, detail="room not found")

    # check if dates overlap with any existing bookings in the system
    for res in reservations:
        if res.get('room_id') == booking.room_id:
            # simple string comparison to see if check-in/check-out dates clash
            existing_in = res.get('check_in')
            existing_out = res.get('check_out')
            if existing_in and existing_out:
                try:
                    booked_in = date.fromisoformat(existing_in)
                    booked_out = date.fromisoformat(existing_out)
                except (TypeError, ValueError):
                    continue
                if start_date < booked_out and end_date > booked_in:
                    raise HTTPException(status_code=409, detail="dates are already booked")

    # Calculate and store the same itemized quote exposed by GET /pricing/quote.
    quote = calculate_quote(found_room_type, booking.check_in, booking.check_out)

    # create the new booking dictionary to save
    new_book = {
        "reservation_id": str(uuid.uuid4()),
        "user_id": booking.user_id,
        "room_id": booking.room_id,
        "room_type": found_room_type,
        "check_in": booking.check_in,
        "check_out": booking.check_out,
        "total_price": quote["total_price"],
        "price_breakdown": quote,
        "status": "prebooked"
    }

    # add it to the list and overwrite the file
    reservations.append(new_book)
    write_json('reservations.json', reservations)
    
    return new_book

# 2. get all reservations (with optional filters)
@router.get("/api/bookings")
def get_bookings(
    status: str = Query(None),
    room_id: int = Query(None),
    x_role: str = Header(...)
):
    # only staff should see all bookings
    if x_role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="only admins can see this")

    all_res = read_json('reservations.json')
    result = []

    # loop through and filter results based on what the user asked for
    for res in all_res:
        add_it = True
        if status != None and res.get('status') != status:
            add_it = False
        if room_id != None and res.get('room_id') != room_id:
            add_it = False
        
        if add_it == True:
            result.append(res)
            
    return result

# 3. get bookings for a specific user
@router.get("/api/bookings/{user_id}")
def get_user_bookings(user_id: str = Path(..., min_length=2, max_length=8), x_role: str = Header(...)):
    if x_role == "":
        raise HTTPException(status_code=401, detail="role is missing")

    res = read_json('reservations.json')
    my_books = []
    
    # find all bookings matching this user id
    for r in res:
        if r.get('user_id') == user_id:
            my_books.append(r)
    
    if len(my_books) == 0:
        raise HTTPException(status_code=404, detail="no bookings for this user")
        
    return my_books

# 4. delete a user and wipe their bookings
@router.delete("/api/users/{user_id}", status_code=204)
def delete_user_stuff(user_id: str = Path(..., min_length=2, max_length=8), x_role: str = Header(...)):
    # strictly admin only
    if x_role != "admin":
        raise HTTPException(status_code=403, detail="only admin can delete")

    users = read_json('users.json')
    res = read_json('reservations.json')

    # check if user actually exists first
    found = False
    for u in users:
        if u.get('user_id') == user_id:
            found = True
    
    if not found:
        raise HTTPException(status_code=404, detail="user not found")

    # rebuild lists from scratch without the deleted user
    new_users = []
    for u in users:
        if u.get('user_id') != user_id:
            new_users.append(u)

    new_res = []
    for r in res:
        if r.get('user_id') != user_id:
            new_res.append(r)

    # save the freshly cleaned lists
    write_json('users.json', new_users)
    write_json('reservations.json', new_res)
    
    return