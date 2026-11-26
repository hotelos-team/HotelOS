import json
from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import APIRouter
from storage import read_data,write_data
import time
import threading 
import simulation_clock



router = APIRouter()

def room_cleaning(room_id: int):
    time.sleep(30)
    
    room_types = read_data("rooms.json")
    for group in room_types:
        for room in group["room"]:

            if room["room_id"] == room_id:
                
                if room["clean"]:
                    raise HTTPException(
                        status_code=409,
                        detail="Room does not require cleaning"
                    )

                if room["status"] != "empty":
                    raise HTTPException(
                        status_code=409,
                        detail="Room is occupied"
                    )
                room["clean"] = True
                room["status"] = "empty"

                write_data("rooms.json", room_types)

                return {"message": "Housekeeping completed"}

    raise HTTPException(
        status_code=404,
        detail="Room ID not found"
    )

@router.get("/rooms/{room_type}")
def get_available_rooms(room_type: str):
    room_types = read_data("rooms.json")

    for group in room_types:
        if group["type"] == room_type:
            available_rooms = []

            for room in group["room"]:
                if room["status"] == "empty" and room["clean"] is True:
                    available_rooms.append(room)

            return available_rooms

    raise HTTPException(
        status_code=404,
        detail="Invalid room type"
    )


@router.post("/reservations/{reservation_id}/check-in/{user_id}")
def check_in(reservation_id: int, user_id: int):

    room_types = read_data("rooms.json")
    reservations = read_data("reservations.json")
    users = read_data("users.json")

    # 1. Check whether the reservation exists
    reservation = None

    for item in reservations:
        if item["id"] == reservation_id:
            reservation = item
            break

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation ID not found"
        )

    # 2. Check whether the user exists
    user_exists = False

    for user in users:
        if user["user_id"] == user_id:
            user_exists = True
            break

    if not user_exists:
        raise HTTPException(
            status_code=404,
            detail="User ID not found"
        )

    # 3. Find the room using its room_id
    target_room = None

    for group in room_types:
        for room in group["room"]:
            if room["room_id"] == reservation["room_id"]:
                target_room = room
                break

        if target_room is not None:
            break

    if target_room is None:
        raise HTTPException(
            status_code=404,
            detail="Room ID not found"
        )

    # 4. Check whether the room is available and clean
    if target_room["status"] != "empty" or not target_room["clean"]:
        raise HTTPException(
            status_code=409,
            detail="Room is not available for check-in"
        )

    # 5. Update room status
    target_room["status"] = "occupied"
    target_room["checkin_time"] = clock.now().isoformat()

    # 6. Save the entire nested room structure
    write_data("rooms.json", room_types)

    return {
        "message": "Check-in successful",
        "reservation_id": reservation_id,
        "room_id": reservation["room_id"]
    }

@router.post("/reservations/{reservation_id}/check-out/{user_id}")
def check_out(user_id,reservation_id : int):

    room_types = read_data("rooms.json")
    reservations = read_data("reservations.json")
    users = read_data("users.json")

    # 1. Check whether the reservation exists
    reservation = None

    for item in reservations:
        if item["id"] == reservation_id:
            reservation = item
            break

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation ID not found"
        )

    # 2. Check whether the user exists
    user_exists = False

    for user in users:
        if user["user_id"] == user_id:
            user_exists = True
            break

    if not user_exists:
        raise HTTPException(
            status_code=404,
            detail="User ID not found"
        )

    # 3. Find the room using its room_id
    target_room = None

    for group in room_types:
        for room in group["room"]:
            if room["room_id"] == reservation["room_id"]:
                target_room = room
                break

        if target_room is not None:
            break

    if target_room is None:
        raise HTTPException(
            status_code=404,
            detail="Room ID not found"
        )

    # 4. Check whether the room is available and clean
    if target_room["status"] != "empty" or not target_room["clean"]:
        raise HTTPException(
            status_code=409,
            detail="Room is not available for check-in"
        )

    # 5. Update room status
    target_room["checkout_time"] = clock.now().isoformat()
    target_room["clean"] = False
    target_room["status"] = "cleaning"
    # 6. Save the entire nested room structure
    write_data("rooms.json", room_types)

    t1 = threading.Thread(
    target=room_cleaning, args=(target_room["room_id"],))
    t1.start()
    return {
        "message": "Check-in successful",
        "reservation_id": reservation_id,
        "room_id": reservation["room_id"]
    }




    

