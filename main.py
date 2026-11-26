import json
from dotenv import load_dotenv


from pydantic import BaseModel
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from prebook import router as prebook_router
from routers.pricing import router as pricing_router
from routers.stays import router as stays_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hotel-os-wheat-eight.vercel.app",
        "https://hotel-low5ejwuf-sant0xdev.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Accept", "Content-Type", "X-Role", "Authorization"],
)
app.include_router(prebook_router)
app.include_router(pricing_router)
app.include_router(stays_router)

class User(BaseModel):
    username: str
    password: str
@app.get("/",tags=["Server"])
def home():
    return {"OUR FIRST PROJECT ":"HOTEL OS"}
#returns if the server is running or not
#if not found return then show USER DATA NULL
@app.get("/health",tags=["Server"])
def health():
    return {"status": "ok"}

#Gives the users.json file asked by Admin only
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
#returns None is it is true
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
        raise HTTPException(status_code = 400,detail = "Invalid entry")
    #Checks if username already exists
    for user in data:
        if username==user["username"]:
            raise HTTPException(status_code = 409,detail = f"Conflict {username} already exists")
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
        raise HTTPException(status_code=404,detail="users.json file does not exist")

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


#customer search function via username
#anyone can search for username
@app.get("/customers/id/{username}",tags=["Searching"])
def customer_id(username:str):
    if not os.path.exists('users.json'):
        raise HTTPException(status_code = 404,detail = 'user data null')

    all_data = data_giver_user()
    for user in all_data:
        if user.get("username",'').strip() == username.strip():
            return {'user_id':user.get("user_id")}
    raise HTTPException(status_code = 404,detail = 'user doesn\'t exist')

#customer search via user_id
@app.get("/customers/search/{id}",tags=["Searching"])
def customer_search(id : int):
    if not os.path.exists("users.json"):
        raise HTTPException(status_code = 404 , detail = 'user data null')

    all_data = data_giver_user()
    for user in all_data:
        if user.get('user_id') == id:
            return {'username' : user.get("username")}
    raise HTTPException(status_code = 404 , detail = 'id doesnt\'t exist')


#Deletion of user from the user.json database
#can be deleted only if the x_role is User or Admin
#x_role is the query parameter
@app.delete("/customer/delete/{username}/{password}",tags=["Delete"])
def delete_customer(username:str,password:str,x_role:str='User'):
    if(check_role(x_role,allowed=["User","Admin"])==None):
        if not os.path.exists('users.json'):
            raise HTTPException(status_code=404, detail='file doesn\'t exist')

        all_data = data_giver_user()
        clean_username = username.strip()

        for user in all_data:
            if user.get('username') == clean_username:
                if decrypter(user.get("password")) != password:
                    raise HTTPException(status_code=403, detail='Password Incorrect')

                all_data.remove(user)
                with open("users.json", "w") as file:
                    json.dump(all_data, file, indent=2)

                return {"message": "deleted"}
    else:
        raise HTTPException(status_code=404, detail='User dosen\'t exist')

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
    if os.path.exists("rooms.json"):
        with open('rooms.json','r') as file:
            data=json.load(file)
            return data
    else:
        return None
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
