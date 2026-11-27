"""Additive UI entry point. Run: python -m uvicorn web_app:app --reload --port 8001"""
from pathlib import Path
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.routing import Mount
from main import app
from services import authenticate, read_records, same_id

FRONTEND = Path(__file__).resolve().parent / 'frontend'
# Put assets ahead of main.py's /{x_role}/{password} catch-all route.
app.router.routes.insert(0, Mount('/hotel-assets', app=StaticFiles(directory=FRONTEND), name='hotel-assets'))

@app.get('/', include_in_schema=False)
def website():
    return FileResponse(FRONTEND / 'index.html')

class LoginIn(BaseModel):
    username: str
    password: str

@app.post('/api/ui/login', tags=['Website'])
def website_login(body: LoginIn):
    # JSON body keeps passwords out of URL paths and access-log URLs.
    if not body.username.isascii() or not body.password.isascii() or ':' in body.username:
        raise HTTPException(422, 'This prototype supports ASCII credentials and usernames without colons.')
    try:
        return authenticate(HTTPBasicCredentials(username=body.username, password=body.password))
    except HTTPException as exc:
        if exc.status_code == 401:
            raise HTTPException(403, 'Incorrect username or password') from exc
        raise

@app.get('/api/ui/reservations', tags=['Website'])
def website_reservations(actor=Depends(authenticate)):
    # Authenticate on the server, then filter guest ownership. No client role claims.
    fields = ('reservation_id', 'id', 'room_id', 'status', 'check_in', 'check_out')
    return [{key: row[key] for key in fields if key in row}
            for row in read_records('reservations.json')
            if actor['role'] != 'User' or same_id(row.get('user_id'), actor['user_id'])]
