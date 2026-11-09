import json
from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import FastAPI
import os
from storage import read_data,write_data
import time
import threading 


#later in the project
"""
class User(BaseModel):
    reservation_id :int = Field(default = max(dic["id"] for dic in open("reservation.json","r")))

#pre-booking
def booking(user_id):
    generate room_id and reservation_id beforehand based on stored data"""


def check_in(user_id,reservation_id : int):
    #rooms = read_data("rooms.json")
    #reservations = read_data("reservations.json")
    # users = read_data("users.json")
    for reservation in reservations:
        if reservation["id"] == reservation_id:
            #now check for whether the user exist in the database(users.json)
            for user in users :
                if user["user_id"] == user_id:
                    for room in rooms:
                        if room["room_id"] == reservation["room_id"]:
                            room["availability_status"] = "occupied"
                            write_data("rooms.json", rooms)
                            room["checkout_in"] = clock.now().isoformat()
                            return "success"

                    return "room_id not found"
            return "user_id not found"
    return "reservation_ id not found"

def check_out(user_id,reservation_id : int):
    #rooms = read_data("rooms.json")
    #reservations = read_data("reservations.json")
    #users = read_data("users.json")
    for reservation in reservations:
        if reservation["id"] == reservation_id:
            #now check for whether the user exist in the database(users.json)
            for user in users :
                if user["user_id"] == user_id:
                    for room in rooms:
                        if room["room_id"] == reservation["room_id"]:
                            room["checkout_time"] = clock.now().isoformat()
                            room["cleaning_status"] = "pending"
                            room["availability_status"] = "dirty"
                            write_data("rooms.json", rooms)
                            return "success"

                    return "room_id not found"
            return "user_id not found"
    return "reservation_ id not found"

def room_cleaning(room_id: int):
    rooms = read_data("rooms.json")
    for room in rooms:
        if room["room_id"] == room_id:
            if room["cleaning_status"] != "pending":
                return "Room does not require cleaning"
            checkout_time = datetime.fromisoformat(
                room["checkout_time"]
            )
            cleaning_duration = timedelta(minutes=30) #30 minutes which is 30s in our simulated clock
            if clock.now() < checkout_time + cleaning_duration:
                return "Cleaning is still in progress"
            room["cleaning_status"] = "clean"
            room["availability_status"] = "available"
            write_data("rooms.json", rooms)
            return "Housekeeping completed"

    return "room_id not found"

    

