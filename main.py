import json
from dotenv import load_dotenv


from pydantic import BaseModel
from fastapi import FastAPI,HTTPException
import os
app = FastAPI()

class User(BaseModel):
    username: str
    password: str

"""sayak"""
#gives the largest user_id number from the users.json
def find_largest_id():
    data=data_giver_user()
    max=0
    for user in data:
        if( user["user_id"]>max):
            max=user["user_id"]
    return max

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
load_dotenv("important.env")
def encrypter(text:str) -> str:
    a=int(os.getenv("a"))
    b=int(os.getenv("b"))
    if text==None:
        return ""
    else:
        encryp=""
        for ch in text:
            encryp+=chr(ord(ch)*a+b)
        return encryp

#Decrypter function using keys a and b
def decrypter(text:str) -> str:
    a = int(os.getenv("a"))
    b = int(os.getenv("b"))
    if(text==None):
        return ""
    else:
        decryp=""
        for ch in text:
            decryp+=chr((ord(ch) - b) // a)

        return decryp

#returns if the server is running or not
@app.get("/health",tags=["Server"])
def health():
    return {"status": "ok"}

#Gives the users.json file asked by user
@app.get("/users/{x_role}/{password}",tags=["Server"])
def users_data(x_role:str="",password:str=""):
    if(check_role(x_role,allowed=['Admin'])==None and admin_or_service_login(x_role,password)=='Success'):

        #if json file does not exist
        if not os.path.exists("users.json"):
                return {"message": "no users found"}

        data=data_giver_user()
        return data
    else:
        raise HTTPException(status_code=403,detail=f"The role {x_role} is not allowed to see")

#Gives rooms.json only if the x_role is Admin
@app.get("/rooms/{x_role}/{password}",tags=["Server"])
def rooms_data(x_role:str="",password:str=""):
    if(check_role(x_role,allowed=['Admin'])==None and admin_or_service_login(x_role,password)=='Success'):

        #if json file does not exist
        if not os.path.exists("rooms.json"):
                return {"message": "no users found"}

        data=data_giver_room()
        return data
    else:
        raise HTTPException(status_code=403,detail=f"The role {x_role} is not allowed to see")

#for checking roles ie Admin || Service || User
def check_role(x_role,allowed):
    if x_role not in ('User','Admin','Service'):
        raise HTTPException(status_code=401,detail="Send the header X-Role with Admin or Service or User")

    if x_role not in allowed:
        raise HTTPException(status_code=403,detail=f"The role {x_role} is not allowed in {allowed}")
#user entry signup and login functions and id generation with password encryption
#assumption username are all different
#?x_role=User(must be)
@app.post("/signup/{username:str}/{password:str}",tags=["USER"])
def sign_up(username:str="",password:str="",x_role:str='User'):
    check_role(x_role,allowed=['User'])
    #if json file doesnot exit then creates
    if not os.path.exists("users.json"):
        with open("users.json","w") as file:
            json.dump([],file,indent=2)
    #loads data
    data=data_giver_user()
    #Checks if the username and password is "" or not
    if(username.strip()=="" or password.strip()==""):
        return {"message":"Empty input"}
    #Checks if username already exists
    for user in data:
        if username==user["username"]:
            return "username already exists"
    #write the json file with new entry
    max=find_largest_id()+1
    with open("users.json","w") as file:
        new_entry={"user_id":max,"username":username.strip(),"password":encrypter(password.strip())}
        data.append(new_entry)
        json.dump(data,file,indent=2)
        return "success"

#login for user except admin,service
#x_role as query parameter
@app.get("/login/{username:str}/{password:str}",tags=["USER"])
def login(username:str=None,password:str=None,x_role:str='User'):
    check_role(x_role,allowed=['User'])
#if users.json DNE
    if not os.path.exists("users.json"):
        return "file does not exist"

    data=data_giver_user()

    for user in data:
        if user["username"]==username:
            if decrypter(user["password"])==password:
                return "Login Successful"
            else:
                return "Password Incorrect"
    return "User does not exist"

#login for admin
@app.get("/{x_role}/{password}",tags=["Staff"])
def admin_or_service_login(x_role:str=None,password:str=None):
    check_role(x_role,allowed=['Admin','Service'])
    if(x_role=="Admin" and password==os.getenv("Admin_pass")):
        return 'Success'
    elif(x_role=="Service" and password==os.getenv("Service_pass")):
        return 'Success'
    else:
        raise HTTPException(status_code=403,detail="The password is incorrect")

