# FastAPI User Authentication & Management API

A lightweight backend application built with **FastAPI** that manages user registration, authentication, and basic server metrics. It uses local JSON file storage (`users.json`) and a custom affine cipher encryption routine.

---

## 📋 Features

- **Server Health Check**: Quickly verify server status.
- **User Signup**: Registers users with randomly generated IDs ($2-1000$) and encrypted passwords.
- **Auto-Initialization**: Creates `users.json` with a default `Admin` account if it doesn't already exist.
- **User Authentication**: Validates standard user credentials against encrypted records.
- **Admin Authentication**: Dedicated route for checking admin password credentials.
- **Data Inspection**: View stored user data directly via an endpoint.

---

## 🛠️ Prerequisites & Installation

Ensure you have Python 3.8+ installed. Install the required dependencies using `pip`:

```bash
pip install fastapi uvicorn pydantic
```

---

## 🏃 Getting Started

1. Save your code into a Python file named `main.py`.
2. Start the FastAPI development server:

```bash
uvicorn main:app --reload
```

3. Access the interactive documentation in your browser at:
   - **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔌 API Endpoints & Usage Examples

Below are all available endpoints with ready-to-copy `cURL` commands and URL formats.

---

### 1. Server Health Check

Checks if the API server is up and operational.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/health`

**cURL Command:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/health' \
  -H 'accept: application/json'
```

**Response Example:**
```json
{
  "status": "ok"
}
```

---

### 2. Get All Users Data

Retrieves the raw user entries stored in `users.json`.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/users`

**cURL Command:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users' \
  -H 'accept: application/json'
```

**Response Example:**
```json
[
  {
    "user_id": 1,
    "username": "Admin",
    "password": "..."
  },
  {
    "user_id": 482,
    "username": "johndoe",
    "password": "..."
  }
]
```

---

### 3. User Signup

Registers a new user and appends their credentials to `users.json`. 

- **Method**: `POST`
- **URL Pattern**: `http://127.0.0.1:8000/signup/{username}/{password}`

**cURL Command:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/signup/johndoe/mypassword123' \
  -H 'accept: application/json'
```

**Response Options:**
- `"success"` — User successfully created.
- `"username already exists"` — User already registered.

---

### 4. User Login

Authenticates standard user accounts. Disallows direct login for the `Admin` username.

- **Method**: `GET`
- **URL Pattern**: `http://127.0.0.1:8000/login/{username}/{password}`

**cURL Command:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/login/johndoe/mypassword123' \
  -H 'accept: application/json'
```

**Response Options:**
- `"login successful"`
- `"password incorrect"`
- `"User does not exist"`
- `"No access"` (if username is `Admin`)
- `"file does not exist"`

---

### 5. Admin Login

Validates credentials against the primary Admin account (first index of `users.json`).

- **Method**: `GET`
- **URL Pattern**: `http://127.0.0.1:8000/admin/{password}`

**cURL Command:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/admin/123' \
  -H 'accept: application/json'
```

**Response Options:**
- `"Success"`
- `"Failure"`

---

## 🔒 Security Notice

This application uses a custom mathematical shift algorithm (`chr(ord(text[i]) * 11 + 17)`) for demonstration purposes. For production applications, always use industry-standard hashing implementations like **bcrypt** or **Argon2** via packages such as `passlib`.