"""HotelOS service router. Run with one Uvicorn worker (JSON prototype).

Uses existing users.json passwords and important.env for compatibility.
An active reservation must have status='checked_in' and its room occupied.
Money is stored as integer paise. No room charges or payments are modified.
"""
import json
import os
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, Union
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / 'important.env')
router = APIRouter(prefix='/api/services', tags=['Services'])
security = HTTPBasic()
# Protect service-file read/modify/write operations within ONE server process.
store_lock = threading.RLock()

# Example prices: confirm these with your team before use.
MENU = {
    'veg_sandwich': {'name': 'Veg sandwich', 'category': 'food', 'price_paise': 12000},
    'veg_thali': {'name': 'Veg thali', 'category': 'food', 'price_paise': 22000},
    'pasta': {'name': 'Pasta', 'category': 'food', 'price_paise': 18000},
    'tea': {'name': 'Tea', 'category': 'beverage', 'price_paise': 3000},
    'coffee': {'name': 'Coffee', 'category': 'beverage', 'price_paise': 5000},
    'lime_soda': {'name': 'Lime soda', 'category': 'beverage', 'price_paise': 6000},
}


def read_records(filename, allow_missing=False):
    """Never silently replace corrupt data with an empty list."""
    path = BASE_DIR / filename
    try:
        with path.open(encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        if allow_missing:
            return []
        raise HTTPException(503, f'{filename} is missing; initialize hotel data first')
    except (json.JSONDecodeError, UnicodeError, OSError):
        raise HTTPException(503, f'Cannot read {filename}; ask staff to check it')
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise HTTPException(503, f'{filename} must contain a JSON list of objects')
    return data


def save_requests(rows):
    """Atomically replace only services.json; caller holds store_lock."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=BASE_DIR, delete=False) as file:
            temporary = Path(file.name)
            json.dump(rows, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, BASE_DIR / 'services.json')
    except OSError:
        raise HTTPException(503, 'Unable to save service requests')
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def same_id(first, second):
    return first is not None and second is not None and str(first) == str(second)


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    """Swagger Authorize accepts existing guest credentials or staff credentials."""
    username = credentials.username
    password = credentials.password
    if username in ('Admin', 'Service'):
        expected = os.getenv(username + '_pass')
        if expected and secrets.compare_digest(password.encode(), expected.encode()):
            return {'role': username, 'user_id': None}
    else:
        for user in read_records('users.json'):
            if user.get('username') != username:
                continue
            try:
                a, b = int(os.environ['a']), int(os.environ['b'])
                if a <= 0:
                    raise ValueError
                encoded = ''.join(chr(ord(char) * a + b) for char in password)
            except (KeyError, ValueError, OverflowError):
                raise HTTPException(503, 'Guest password configuration is invalid')
            stored = user.get('password')
            if (user.get('user_id') is not None and isinstance(stored, str)
                    and secrets.compare_digest(encoded.encode(), stored.encode())):
                return {'role': 'User', 'user_id': user['user_id']}
            break
    raise HTTPException(401, 'Incorrect credentials', headers={'WWW-Authenticate': 'Basic'})


def staff_only(actor=Depends(authenticate)):
    if actor['role'] not in ('Admin', 'Service'):
        raise HTTPException(403, 'Only staff can do this')
    return actor


def get_reservation(reservation_id, actor, active=False):
    for row in read_records('reservations.json'):
        if same_id(row.get('reservation_id', row.get('id')), reservation_id):
            if actor['role'] == 'User' and not same_id(row.get('user_id'), actor['user_id']):
                raise HTTPException(403, 'This reservation does not belong to you')
            if not active:
                return row
            if row.get('status') != 'checked_in':
                raise HTTPException(409, 'Services require reservation status checked_in')
            for group in read_records('rooms.json'):
                for room in group.get('room', []):
                    if same_id(room.get('room_id'), row.get('room_id')):
                        if room.get('status') != 'occupied':
                            raise HTTPException(409, 'The reserved room is not occupied')
                        return row
            raise HTTPException(404, 'Room not found')
    raise HTTPException(404, 'Reservation not found')


class ServiceIn(BaseModel):
    reservation_id: str = Field(min_length=1, max_length=100)
    notes: str = Field(default='', max_length=500)


class OrderItem(BaseModel):
    item_id: str = Field(min_length=1, max_length=60)
    quantity: int = Field(default=1, ge=1, le=20, strict=True)


class FoodIn(ServiceIn):
    category: Literal['food']
    items: list[OrderItem] = Field(min_length=1, max_length=20)


class BeverageIn(ServiceIn):
    category: Literal['beverage']
    items: list[OrderItem] = Field(min_length=1, max_length=20)


class CleaningIn(ServiceIn):
    category: Literal['cleaning']
    guest_in_room: bool = True
    permission_to_enter: bool = False


RequestIn = Annotated[Union[FoodIn, BeverageIn, CleaningIn], Field(discriminator='category')]


class StatusIn(BaseModel):
    status: Literal['in_progress', 'completed', 'cancelled']


def create_request(body, category, details, amount_paise, actor):
    reservation = get_reservation(body.reservation_id, actor, active=True)
    now = datetime.now(timezone.utc).isoformat()
    record = {
        'service_id': str(uuid4()), 'reservation_id': body.reservation_id,
        'user_id': reservation.get('user_id'), 'room_id': reservation['room_id'],
        'category': category, 'details': details, 'notes': body.notes.strip(),
        'amount_paise': amount_paise, 'currency': 'INR', 'status': 'pending',
        'created_at': now, 'updated_at': now,
    }
    with store_lock:
        rows = read_records('services.json', allow_missing=True)
        rows.append(record)
        save_requests(rows)
    return record


def order(body, category, actor):
    details, total = [], 0
    for item in body.items:
        entry = MENU.get(item.item_id)
        if entry is None or entry['category'] != category:
            raise HTTPException(400, f'Invalid {category} item: {item.item_id}')
        subtotal = entry['price_paise'] * item.quantity
        total += subtotal
        details.append({'item_id': item.item_id, 'name': entry['name'],
                        'quantity': item.quantity, 'unit_price_paise': entry['price_paise'],
                        'subtotal_paise': subtotal})
    return create_request(body, category, {'items': details}, total, actor)


@router.get('/menu')
def get_menu():
    return {'currency': 'INR',
            'items': [{'item_id': key, **value} for key, value in MENU.items()],
            'cleaning_price_paise': 0}


@router.post('/requests', status_code=201)
def place_request(body: RequestIn, actor=Depends(authenticate)):
    if body.category == 'cleaning':
        return create_request(body, 'cleaning',
                              {'guest_in_room': body.guest_in_room,
                               'permission_to_enter': body.permission_to_enter}, 0, actor)
    return order(body, body.category, actor)


@router.get('/requests')
def list_requests(status: Optional[Literal['pending', 'in_progress', 'completed', 'cancelled']] = None,
                  actor=Depends(authenticate)):
    with store_lock:
        rows = read_records('services.json', allow_missing=True)
    # Guests see only their own requests; authenticated staff see all.
    return [row for row in rows
            if (actor['role'] != 'User' or same_id(row.get('user_id'), actor['user_id']))
            and (status is None or row.get('status') == status)]


def find_request(rows, service_id, actor):
    for row in rows:
        if row.get('service_id') == service_id:
            if actor['role'] == 'User' and not same_id(row.get('user_id'), actor['user_id']):
                raise HTTPException(403, 'This request does not belong to you')
            return row
    raise HTTPException(404, 'Service request not found')


@router.patch('/requests/{service_id}/status')
def update_status(service_id: str, body: StatusIn, actor=Depends(staff_only)):
    allowed = {'pending': {'in_progress', 'cancelled'},
               'in_progress': {'completed', 'cancelled'}, 'completed': set(), 'cancelled': set()}
    with store_lock:
        rows = read_records('services.json', True)
        row = find_request(rows, service_id, actor)
        if body.status not in allowed.get(row['status'], set()):
            raise HTTPException(409, f'Cannot change {row["status"]} to {body.status}')
        # Do not dispatch new work to a guest who has already checked out.
        if body.status == 'in_progress':
            get_reservation(row['reservation_id'], actor, active=True)
        row['status'] = body.status
        row['updated_at'] = datetime.now(timezone.utc).isoformat()
        save_requests(rows)
        return row
