from fastapi import APIRouter, HTTPException, Header, Query, Path
from pydantic import BaseModel, Field
import json
import uuid

# setting up router so it doesn't clutter up the main file
router = APIRouter(tags = ["Prebooking"])

# my input model for the post request
# using Field to make sure the user_id is between 2 and 8 characters long!
class PrebookIn(BaseModel):
    user_id: str = Field(min_length=2, max_length=8)
    room_id: int = Field(...) 
    check_in: str = Field(...)
    check_out: str = Field(...)

# safe function to read json so my server doesnt crash if the file is missing or weird
def read_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return [] # just return an empty list if there's an error

def write_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# model for taking username and password
class UserAuth(BaseModel):
    username: str = Field(min_length=2, max_length=8)
    password: str = Field(min_length=2)

# 5. register a new user from prebook
@router.post("/api/prebook/register", status_code=201)
def register_from_prebook(user: UserAuth):
    # importing here so python doesnt give circular import error with main.py
    from main import encrypter, find_largest_id

    users = read_json('users.json')

    # check if username is already taken
    for u in users:
        if u.get("username") == user.username:
            raise HTTPException(status_code=409, detail="username already exists")

    # get the next id number and encrypt the password like main.py does
    new_id = find_largest_id() + 1
    encrypted_pw = encrypter(user.password)

    # making the new user dict in the same format as users.json
    new_user = {
        "id": new_id,
        "username": user.username,
        "password": encrypted_pw
    }

    # add to list and save back to file
    users.append(new_user)
    write_json('users.json', users)

    return {"message": "user created", "id": new_id, "username": user.username}

# 6. login to check if username and password match
@router.post("/api/prebook/login", status_code=200)
def login_from_prebook(user: UserAuth):
    # same thing, importing inside function to avoid circular import
    from main import encrypter

    users = read_json('users.json')
    encrypted_pw = encrypter(user.password)

    # loop through all users to find a match
    for u in users:
        if u.get("username") == user.username and u.get("password") == encrypted_pw:
            return {"message": "login successful", "id": u.get("id"), "username": u.get("username")}

    # if loop finishes without finding them, password or username is wrong
    raise HTTPException(status_code=401, detail="invalid username or password")

# 1. create a prebooking
@router.post("/api/bookings/prebook", status_code=201)
def make_prebooking(booking: PrebookIn, x_role: str = Header(...)):
    # checking permissions to make sure they are allowed
    if x_role not in ["customer", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="you are not allowed to do this")

    rooms_data = read_json('rooms.json')
    reservations = read_json('reservations.json')

    # we need a double loop because the rooms are hidden inside categories like 'deluxe'
    found_room = False
    for category in rooms_data:
        # get the list of rooms inside this specific category
        room_list = category.get("room", [])
        for r in room_list:
            if r.get("room_id") == booking.room_id:
                found_room = True
    
    if found_room == False:
        raise HTTPException(status_code=404, detail="room not found")

    # check if dates overlap with any existing bookings in the system
    for res in reservations:
        if res.get('room_id') == booking.room_id:
            # simple string comparison to see if check-in/check-out dates clash
            if booking.check_in < res.get('check_out') and booking.check_out > res.get('check_in'):
                raise HTTPException(status_code=409, detail="dates are already booked")

    # create the new booking dictionary to save
    new_book = {
        "reservation_id": str(uuid.uuid4()),
        "user_id": booking.user_id,
        "room_id": booking.room_id,
        "check_in": booking.check_in,
        "check_out": booking.check_out,
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
