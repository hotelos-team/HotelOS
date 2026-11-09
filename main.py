import json
import random
from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import FastAPI
import os
app = FastAPI()

class User(BaseModel):
    username: str
    password: str

"""sayak"""
#Hands over the data from users.json file everytime its called
def data_giver_user():
    if os.path.exists("users.json"):
        with open("users.json","r") as file:
            data=json.load(file)
            return data
    else:
        return None
def data_giver_room():
    with open('rooms.json','r') as file:
        data=json.load(file)
        return data
#Encrypter and decrypter function
a,b=11,17
def encrypter(text:str) -> str:
    if text==None:
        return ""
    else:
        encryp=""
        for i in range(len(text)):
            encryp+=chr(ord(text[i])*a+b)
        return encryp

#Decrypter function using keys a and b
def decrypter(text:str) -> str:
    if(text==None):
        return ""
    else:
        decryp=""
        for i in range(len(text)):
            decryp+=chr((ord(text[i])-b)//a)

        return decryp

#returns if the server is running or not
@app.get("/health",tags=["Server"])
def health():
    return {"status": "ok"}

#Gives the users.json file asked by user
@app.get("/users",tags=["Server"])
def users_data():
    #if json file does not exist
    if not os.path.exists("users.json"):
            return {"no users found"}

    data=data_giver_user()
    return data


#user entry signup and login functions and id generation with password encryption
#assumption username are all different
@app.post("/signup/{username:str}/{password:str}",tags=["USER"])
def sign_up(username:str=None,password:str=None):
    #if json file doesnot exit then creates
    if not os.path.exists("users.json"):
        with open("users.json","w") as file:
            json.dump([{"user_id": 1,"username":"Admin","password":encrypter("123")}],file,indent=2)
    #loads data
    data=data_giver_user()
    #Checks if username already exists
    for user in data:
        if username==user["username"]:
            return "username already exists"
    #write the json file with new entry
    with open("users.json","w") as file:
        new_entry={"user_id":random.randint(2,1000),"username":username.strip(),"password":encrypter(password.strip())}
        data.append(new_entry)
        json.dump(data,file,indent=2)
        return "success"

#login for user except admin
@app.get("/login/{username:str}/{password:str}",tags=["USER"])
def login(username:str=None,password:str=None):
#if users.json DNE
    if not os.path.exists("users.json"):
        return "file does not exist"

    if(username=="Admin"):
        return "No access"

    data=data_giver_user()

    for user in data:
        if user["username"]==username:
            if decrypter(user["password"])==password:
                return "login successful"
            else:
                return "password incorrect"
    return "User does not exist"

#login for admin
@app.get("/admin/{password}",tags=["Admin"])
def admin_login(password:str=None):
    data= data_giver_user()
    if data[0]["password"]==password:
        return "Success"
    else:
        return "Failure"

"""sayak"""