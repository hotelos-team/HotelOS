import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from prebook import router as prebook_router
from routers.pricing import router as pricing_router
from routers.stays import router as stays_router

load_dotenv("important.env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(prebook_router)
app.include_router(pricing_router)
app.include_router(stays_router)


class User(BaseModel):
    username: str
    password: str


@app.get("/", tags=["Server"])
def home():
    return {"OUR FIRST PROJECT ": "HOTEL OS"}


@app.get("/health", tags=["Server"])
def health():
    return {"status": "ok"}


# Gives the users.json file asked by Admin only
@app.get("/users/{x_role}/{password}", tags=["Server"])
def users_data(x_role: str = "", password: str = ""):
    if check_role(x_role, allowed=["Admin"]) is None and admin_or_service_login(x_role, password) == "Success":
        if not os.path.exists("users.json"):
            return {"message": "no users found"}
        return data_giver_user()
    raise HTTPException(status_code=403, detail=f"The role {x_role} is not allowed to see")


# Gives rooms.json only if the x_role is Admin
@app.get("/rooms/{x_role}/{password}", tags=["Server"])
def rooms_data(x_role: str = "", password: str = ""):
    if check_role(x_role, allowed=["Admin"]) is None and admin_or_service_login(x_role, password) == "Success":
        if not os.path.exists("rooms.json"):
            return {"message": "no rooms found"}
        return data_giver_room()
    raise HTTPException(status_code=403, detail=f"The role {x_role} is not allowed to see")


# Checks roles: Admin | Service | User (returns None if valid)
def check_role(x_role, allowed):
    if x_role not in ("User", "Admin", "Service"):
        raise HTTPException(status_code=401, detail="Send the header X-Role with Admin or Service or User")
    if x_role not in allowed:
        raise HTTPException(status_code=403, detail=f"The role {x_role} is not allowed in {allowed}")


@app.post("/signup/{username:str}/{password:str}", tags=["USER"])
def sign_up(username: str = "", password: str = "", x_role: str = "User"):
    check_role(x_role, allowed=["User"])

    if not os.path.exists("users.json"):
        with open("users.json", "w") as file:
            json.dump([], file, indent=2)

    data = data_giver_user() or []

    if username.strip() == "" or password.strip() == "":
        raise HTTPException(status_code=400, detail="Invalid entry")

    for user in data:
        if username == user.get("username"):
            raise HTTPException(status_code=409, detail=f"Conflict {username} already exists")

    new_id = find_largest_id() + 1
    new_entry = {
        "user_id": new_id,
        "username": username.strip(),
        "password": encrypter(password.strip()),
    }
    data.append(new_entry)

    with open("users.json", "w") as file:
        json.dump(data, file, indent=2)

    return "success"


@app.get("/login/{username:str}/{password:str}", tags=["USER"])
def login(username: str = None, password: str = None, x_role: str = "User"):
    check_role(x_role, allowed=["User"])

    if not os.path.exists("users.json"):
        raise HTTPException(status_code=404, detail="users.json file does not exist")

    data = data_giver_user() or []

    for user in data:
        if user.get("username") == username:
            if decrypter(user.get("password")) == password:
                return "Login Successful"
            return "Password Incorrect"

    return "User does not exist"


@app.get("/{x_role}/{password}", tags=["Staff"])
def admin_or_service_login(x_role: str = None, password: str = None):
    check_role(x_role, allowed=["Admin", "Service"])
    if x_role == "Admin" and password == os.getenv("Admin_pass"):
        return "Success"
    elif x_role == "Service" and password == os.getenv("Service_pass"):
        return "Success"
    raise HTTPException(status_code=403, detail="The password is incorrect")


@app.get("/customers/id/{username}", tags=["Searching"])
def customer_id(username: str):
    if not os.path.exists("users.json"):
        raise HTTPException(status_code=404, detail="user data null")

    all_data = data_giver_user() or []
    for user in all_data:
        if user.get("username", "").strip() == username.strip():
            return {"user_id": user.get("user_id") or user.get("id")}
    raise HTTPException(status_code=404, detail="user doesn't exist")


@app.get("/customers/search/{id}", tags=["Searching"])
def customer_search(id: int):
    if not os.path.exists("users.json"):
        raise HTTPException(status_code=404, detail="user data null")

    all_data = data_giver_user() or []
    for user in all_data:
        if (user.get("user_id") or user.get("id")) == id:
            return {"username": user.get("username")}
    raise HTTPException(status_code=404, detail="id doesn't exist")


@app.delete("/customer/delete/{username}/{password}", tags=["Delete"])
def delete_customer(username: str, password: str, x_role: str = "User"):
    check_role(x_role, allowed=["User", "Admin"])

    if not os.path.exists("users.json"):
        raise HTTPException(status_code=404, detail="file doesn't exist")

    all_data = data_giver_user() or []
    clean_username = username.strip()

    for user in all_data:
        if user.get("username") == clean_username:
            if decrypter(user.get("password")) != password:
                raise HTTPException(status_code=403, detail="Password Incorrect")

            all_data.remove(user)
            with open("users.json", "w") as file:
                json.dump(all_data, file, indent=2)

            return {"message": "deleted"}

    raise HTTPException(status_code=404, detail="User doesn't exist")


# Gives the largest user_id number from users.json safely
def find_largest_id():
    data = data_giver_user() or []
    max_id = 0
    for user in data:
        uid = user.get("user_id") or user.get("id") or 0
        if uid > max_id:
            max_id = uid
    return max_id


def data_giver_user():
    if os.path.exists("users.json"):
        with open("users.json", "r") as file:
            return json.load(file)
    return None


def data_giver_room():
    if os.path.exists("rooms.json"):
        with open("rooms.json", "r") as file:
            return json.load(file)
    return None


def encrypter(text: str) -> str:
    a = int(os.getenv("a"))
    b = int(os.getenv("b"))
    if text is None:
        return ""
    return "".join(chr(ord(ch) * a + b) for ch in text)


def decrypter(text: str) -> str:
    a = int(os.getenv("a"))
    b = int(os.getenv("b"))
    if text is None:
        return ""
    return "".join(chr((ord(ch) - b) // a) for ch in text)
